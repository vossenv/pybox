import customlogging
import logging
import click
import re
from subprocess import Popen, PIPE, STDOUT, check_output, call, CalledProcessError

customlogging.initLogger()
logger = logging.getLogger("vbox")

@click.group()
def cli():
    pass

@cli.command()
@click.option('-l', '--vmlist',
              help="comma separated list of VMs (default is 'all')",
              type=str,
              nargs=1)
def start(**kwargs):
    if kwargs['vmlist'] is not None:
        vmlist = [v.strip() for v in kwargs['vmlist'].split(",")]
    else:
        vmlist = get_current_vmlist()


    start_single_vm("new_clone")

    print()

def start_single_vm(name):
    r = shell_exec("vboxmanage startvm " + name + " --type headless")
    pass

@cli.command()
def stop():
    logger.info("Stop")

def get_current_vmlist():
    raw_list, e = shell_exec("vboxmanage list vms")
    if e != 0:
        logger.critical("Failed to get vmlist, error code: " + str(e) + "! Aborting...")
        exit(2)
    return re.findall('(?<=")[^\\\\\n"]+?(?=")', raw_list)

def shell_exec(cmd):
    logger.debug("Executing: " + cmd)
    try:
        r = format_string(check_output(cmd))
        for s in r.split("\n"):
            logger.debug(s)
        return (r, 0)
    except CalledProcessError as e:
        r = str(e)
        logger.warning(r)
        return (r, e.returncode)

def format_string(string):
    try:
        string = str(string.decode()).strip()
    except TypeError:
        string = str(string).strip()
    return string.strip().replace("\r\n","\n")


if __name__ == '__main__':
    cli()
