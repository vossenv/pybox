import logging
import re
import time
import sys
from subprocess import check_output, CalledProcessError

import click

import customlogging

customlogging.initLogger()
logger = logging.getLogger("vbox")


@click.group()
@click.option('--debug', is_flag=True)
@click.option('-l', '--vmlist',
              help="comma separated list of VMs (default is 'all')",
              type=str,
              nargs=1)
@click.pass_context
def cli(ctx, **kwargs):
    logger.setLevel(logging.DEBUG if kwargs['debug'] else logging.INFO)
    vmlist = kwargs['vmlist']
    if vmlist is not None:
        vmlist = [v.strip().replace("\"", "") for v in vmlist.split(",")]
    else:
        vmlist = get_current_vmlist()

    kwargs['vmlist'] = vmlist
    ctx.obj = kwargs


@cli.command()
@click.pass_context
@click.option('--start-delay',
              help="waiting period between VM startups [min]",
              type=int,
              nargs=1,
              default=-1)
def start(ctx, **kwargs):
    logger.info("Starting all virtualmachines... ")
    logger.info("Parameters: ")
    logger.info(kwargs)

    start_delay = kwargs['start_delay']
    vmlist = filter_vmlist(ctx.obj['vmlist'], "halted", True)
    for vm in vmlist:
        success = start_single_vm(vm)
        if len(vmlist) > 1 and vm != vmlist[-1] and success and start_delay != -1.0:
            for i in range(start_delay):
                logger.info("Sleeping for " + str(start_delay) + " minutes, " + str(start_delay - i) + " remaining... ")
                time.sleep(1)
    logger.info("Finished boot sequence for all VM's!")


@cli.command()
@click.pass_context
@click.option('--force', is_flag=True,
              help="how to power down the vm - hard (force) or normal (acpi)")
def stop(ctx, **kwargs):
    logger.info("Stopping all virtualmachines... ")
    logger.info("Parameters: ")
    logger.info(kwargs)

    vmlist = filter_vmlist(ctx.obj['vmlist'], "running", True)
    stop_all(vmlist, force=kwargs['force'])
    logger.info("Finished shutdown sequence for all VM's!")


@cli.command()
@click.pass_context
@click.option('--force', is_flag=True,
              help="how to power down the vm - hard (force) or normal (acpi)")
@click.option('--max-wait-time',
              help="restart will continue after this time (minutes) even if some VM's did not shut down.  Use 0 for never.",
              type=float,
              nargs=1,
              default=1.0)
def restart(ctx, **kwargs):
    logger.info("Restarting virtualmachines... ")
    logger.info("Parameters: ")
    logger.info(kwargs)

    max_wait_time = float(kwargs['max_wait_time']) * 60.0
    vmlist = filter_vmlist(ctx.obj['vmlist'], "running", True)

    if kwargs['force']:
        for vm in vmlist:
            hard_reset_vm(vm)
    else:
        stop_all(vmlist, max_wait=max_wait_time)
        start_all(vmlist)

    logger.info("Finished reboot sequence for all VM's!")


def await_vm_halt(vmlist, max_wait=-1.0):
    if max_wait == -1.0: return True
    start_time = time.time()
    time.sleep(2)
    count = 0
    while True:
        elapsed_time = time.time() - start_time
        remaining = filter_vmlist(vmlist, "running")
        if len(remaining) == 0:
            return True

        if elapsed_time > max_wait and max_wait != 0:
            logger.info("Max wait time exceeded.. continuing on startup... ")
            return False
        else:
            left = "inf" if max_wait == 0 else str(round(max_wait - elapsed_time))
            logger.info("Waiting for VM's to power down, " + left + " seconds remaining... " + str(remaining))
            count += 1
            if count % 5 == 0:
                logger.info("Retrying stop command...")
                stop_all(vmlist, max_wait=-1)
            time.sleep(5)



def filter_vmlist(vmlist, filter, exit_on_empty=False):
    logger.debug("Filtering vm list, and returning all that are: " + filter)
    logger.debug("Starting VM list: " + str(vmlist))

    updated_list = list(vmlist)
    running = get_running_vms()
    if filter == "running":
        for v in vmlist:
            if v not in running:
                logger.info("Skipping " + v + ", already stopped!")
                updated_list.remove(v)
    else:
        for v in running:
            if v in vmlist:
                logger.info("Skipping " + v + ", already running!")
                updated_list.remove(v)

    if len(updated_list) == 0 and exit_on_empty:
        logger.debug("No VM's left in list!! exiting!")
        exit(0)

    logger.debug("Filtered VM list: " + str(updated_list))
    return updated_list


def get_running_vms():
    logger.debug("Fetch running VM's... ")
    running = parse_vm_list(shell_exec("vboxmanage list runningvms")[0])
    return running if running else []


def hard_reset_vm(name):
    logger.info("Attempting to hard restart vm: " + name)
    r, c = shell_exec("vboxmanage controlvm \"" + name + "\" reset")
    if not c: logger.warning("Failed to restart vm: " + name)
    return c


def stop_all(vmlist, force=False, max_wait=-1.0):
    for vm in vmlist:
        stop_single_vm(vm, force=force)
    return await_vm_halt(vmlist, max_wait=max_wait)


def start_all(vmlist):
    for vm in vmlist:
        start_single_vm(vm)


def start_single_vm(name):
    logger.info("Attempting to start vm: " + name)
    r, c = shell_exec("vboxmanage startvm \"" + name + "\" --type headless")
    if not c: logger.warning("Failed to boot vm: " + name)
    return c


def stop_single_vm(name, force=False, max_wait=-1.0):
    method = "poweroff" if force == 'acpi' else "acpipowerbutton"
    logger.info("Attempting to stop vm: " + name)
    r, c = shell_exec("vboxmanage controlvm \"" + name + "\" " + method + " --type headless")
    await_vm_halt(name, max_wait)
    if not c:
        logger.warning("Failed to stop vm: " + name)
        return False


def get_current_vmlist():
    raw_list, e = shell_exec("vboxmanage list vms")
    if not e:
        logger.critical("Failed to get vmlist, error code: " + str(e) + "! Aborting...")
        exit(2)
    return parse_vm_list(raw_list)


def parse_vm_list(raw):
    return re.findall('(?<=")[^\\\\\n"]+?(?=")', raw)


def shell_exec(cmd):
    logger.debug("Executing: " + cmd)
    try:
        r = format_string(check_output(cmd))
        for s in r.split("\n"):
            logger.debug(s)
        return (r, True)
    except (CalledProcessError, WindowsError) as e:
        r = str(e)
        logger.warning(r)
        return (r, False)


def format_string(string):
    try:
        string = str(string.decode()).strip()
    except TypeError:
        string = str(string).strip()
    return string.strip().replace("\r\n", "\n")


if __name__ == '__main__':
    cli(obj={})
