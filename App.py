import logging
import re
import time
import click
import customlogging
from subprocess import check_output, CalledProcessError

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
              default=10)
def start(ctx, **kwargs):
    logger.info("Starting all virtualmachines... ")
    logger.info("Parameters: ")
    logger.info(kwargs)

    start_delay = kwargs['start_delay']
    vmlist = ctx.obj['vmlist']

    logger.info("Removing already running VM's from working list... ")
    for v in parse_vm_list(shell_exec("vboxmanage list runningvms")[0]):
        if v in vmlist:
            logger.info("Skipping " + v + ", already running!")
            vmlist.remove(v)

    logger.info("Final VM list: " + str(vmlist))

    for vm in vmlist:
        success = start_single_vm(vm)
        if len(vmlist) > 1 and vm != vmlist[-1] and success:
            for i in range(start_delay):
                logger.info("Sleeping for " + str(start_delay) + " minutes, " + str(start_delay - i) + " remaining... ")
                time.sleep(1)

    logger.info("Finished boot sequence for all VM's!")


@cli.command()
@click.pass_context
@click.option('--method',
              help="how to power down the vm - hard (force) or normal (acpi)",
              type=click.Choice(['acpi', 'force']),
              nargs=1,
              default='acpi')
def stop(ctx, **kwargs):
    logger.info("Stopping all virtualmachines... ")
    logger.info("Parameters: ")
    logger.info(kwargs)

    method = "acpipowerbutton" if kwargs['method'] == 'acpi' else "poweroff"
    vmlist = ctx.obj['vmlist']

    logger.info("Removing already stopped VM's from working list... ")
    running = get_running_vms()
    for v in vmlist:
        if v not in running:
            logger.info("Skipping " + v + ", already stopped!")
            vmlist.remove(v)

    logger.info("Final VM list: " + str(vmlist))

    if len(vmlist) == 0:
        logger.info("No VM's to stop... exiting!")
        exit(0)

    for vm in vmlist:
        stop_single_vm(vm, method)

    logger.info("Finished shutdown sequence for all VM's!")


def get_running_vms():
    logger.debug("Fetch running VM's... ")
    running = parse_vm_list(shell_exec("vboxmanage list runningvms")[0])
    return running if running else []


def start_single_vm(name):
    logger.info("Attempting to start vm: " + name)
    r, c = shell_exec("vboxmanage startvm \"" + name + "\" --type headless")
    if not c: logger.warning("Failed to boot vm: " + name)
    return c


def stop_single_vm(name, method):
    logger.info("Attempting to stop vm: " + name)
    r, c = shell_exec("vboxmanage controlvm \"" + name + "\" " + method + " --type headless")
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
