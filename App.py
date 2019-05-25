import customlogging
import logging
import click
import time
import re
from subprocess import Popen, PIPE, STDOUT, check_output, call, CalledProcessError

customlogging.initLogger()
logger = logging.getLogger("vbox")


@click.group()
@click.option('--debug/--no-debug', default=False)
@click.option('-l', '--vmlist',
              help="comma separated list of VMs (default is 'all')",
              type=str,
              nargs=1)
@click.pass_context
def cli(ctx, **kwargs):
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
    start_delay = kwargs['start_delay']
    vmlist = ctx.obj['vmlist']

    for v in parse_vm_list(shell_exec("vboxmanage list runningvms")[0]):
        if v in vmlist:
            logger.info("Skipping " + v + ", already running!")
            vmlist.remove(v)

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
    method = "acpipowerbutton" if kwargs['method'] == 'acpi' else "poweroff"
    vmlist = ctx.obj['vmlist']
    running = get_running_vms()
    for v in vmlist:
        if v not in running:
            logger.info("Skipping " + v + ", already stopped!")
            vmlist.remove(v)

    if len(vmlist) == 0:
        logger.info("No VM's to stop... exiting!")
        exit(0)

    for vm in vmlist:
        stop_single_vm(vm, method)

def get_running_vms():
    running = parse_vm_list(shell_exec("vboxmanage list runningvms")[0])
    return running if running else []


def start_single_vm(name):
    r, c = shell_exec("vboxmanage startvm \"" + name + "\" --type headless")
    if not c: logger.warning("Failed to boot vm: " + name)
    return c


def stop_single_vm(name, method):
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
