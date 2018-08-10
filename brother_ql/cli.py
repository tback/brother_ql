#!/usr/bin/env python

# Python standard library
import logging

# external dependencies
import click

# imports from this very package
from brother_ql.devicedependent import models, label_sizes, label_type_specs, DIE_CUT_LABEL, ENDLESS_LABEL, ROUND_DIE_CUT_LABEL
from brother_ql.backends import available_backends, backend_factory


logger = logging.getLogger('brother_ql')


printer_help = "The identifier for the printer. This could be a string like tcp://192.168.1.21:9100 for a networked printer or usb://0x04f9:0x2015/000M6Z401370 for a printer connected via USB."
@click.group()
@click.option('-b', '--backend', type=click.Choice(available_backends), envvar='BROTHER_QL_BACKEND')
@click.option('-m', '--model', type=click.Choice(models), envvar='BROTHER_QL_MODEL')
@click.option('-p', '--printer', metavar='PRINTER_IDENTIFIER', envvar='BROTHER_QL_PRINTER', help=printer_help)
@click.option('--debug', is_flag=True)
@click.version_option()
@click.pass_context
def cli(ctx, *args, **kwargs):
    """ Command line interface for the brother_ql Python package. """

    backend = kwargs.get('backend', None)
    model = kwargs.get('model', None)
    printer = kwargs.get('printer', None)
    debug = kwargs.get('debug')

    # Store the general CLI options in the context meta dictionary.
    # The name corresponds to the second half of the respective envvar:
    ctx.meta['MODEL'] = model
    ctx.meta['BACKEND'] = backend
    ctx.meta['PRINTER'] = printer

    logging.basicConfig(level='DEBUG' if debug else 'INFO')

@cli.command()
@click.pass_context
def discover(ctx):
    """ find connected label printers """
    backend = ctx.meta.get('BACKEND', 'pyusb')
    discover_and_list_available_devices(backend)

def discover_and_list_available_devices(backend):
    from brother_ql.backends.helpers import discover
    available_devices = discover(backend_identifier=backend)
    from brother_ql.output_helpers import log_discovered_devices, textual_description_discovered_devices
    log_discovered_devices(available_devices)
    print(textual_description_discovered_devices(available_devices))

@cli.command()
@click.argument('info', click.Choice(('labels', 'models')))
@click.pass_context
def info(ctx, *args, **kwargs):
    """ list available choices (for labels or models) """
    if kwargs['info'] == 'models':
        """List the models (choices for --model)
        
        List the models that can be used with this software.
        Those are the choices avaiable for the --model option.
        """
        print('Supported models:')
        for model in models: print(" " + model)

    elif kwargs['info'] == 'labels':
        """
        List labels (types and sizes).

        This command lists all labels (label types and label sizes)
        that can be used with this software. """
        from brother_ql.output_helpers import textual_label_description
        print(textual_label_description(label_sizes))

@cli.command('print', short_help='Print a label')
@click.argument('images', nargs=-1, metavar='IMAGE [IMAGE] ...')
@click.option('-l', '--label', type=click.Choice(label_sizes), envvar='BROTHER_QL_LABEL', help='The label (size, type - die-cut or endless). Run `brother_ql info labels` for a full list including ideal pixel dimensions.')
@click.option('-r', '--rotate', type=click.Choice(('auto', '0', '90', '180', '270')), default='auto', help='Rotate the image (counterclock-wise) by this amount of degrees.')
@click.option('-t', '--threshold', type=float, default=70.0, help='The threshold value (in percent) to discriminate between black and white pixels.')
@click.option('-d', '--dither', is_flag=True, help='Enable dithering when converting the image to b/w. If set, --threshold is meaningless.')
@click.option('-c', '--compress', is_flag=True, help='Enable compression (if available with the model). Label creation can take slightly longer but the resulting instruction size is normally considerably smaller.')
@click.option('--red', is_flag=True, help='Create a label to be printed on black/red/white tape (only with QL-8xx series on DK-22251 labels). You must use this option when printing on black/red tape, even when not printing red.')
@click.option('--600dpi', 'dpi_600', is_flag=True, help='Print with 600x300 dpi available on some models. Provide your image as 600x600 dpi; perpendicular to the feeding the image will be resized to 300dpi.')
@click.option('--lq', is_flag=True, help='Print with low quality (faster). Default is high quality.')
@click.option('--no-cut/--cut', is_flag=True, help="Don't cut the tape after printing the label.")
@click.pass_context
def print_cmd(ctx, *args, **kwargs):
    """ Print a label of the provided IMAGE. """
    backend = ctx.meta.get('BACKEND', 'pyusb')
    model = ctx.meta.get('MODEL')
    printer = ctx.meta.get('PRINTER')
    from brother_ql.conversion import convert
    from brother_ql.backends.helpers import send
    from brother_ql.raster import BrotherQLRaster
    qlr = BrotherQLRaster(model)
    qlr.exception_on_warning = True
    instructions = convert(qlr=qlr, **kwargs)
    send(instructions=instructions, printer_identifier=printer, backend_identifier=backend, blocking=True)

@cli.command(name='analyze', help='interpret a binary file containing raster instructions for the Brother QL-Series printers')
@click.argument('instructions', type=click.File('rb'))
@click.option('-f', '--filename-format', help="Filename format string. Default is: label{counter:04d}.png.")
@click.pass_context
def analyze_cmd(ctx, *args, **kwargs):
    from brother_ql.reader import BrotherQLReader
    br = BrotherQLReader(kwargs.get('instructions'))
    if kwargs.get('filename_format'): br.filename_fmt = kwargs.get('filename_format')
    br.analyse()

@cli.command(name='send', short_help='send an instruction file to the printer')
@click.argument('instructions', type=click.File('rb'))
@click.pass_context
def send_cmd(ctx, *args, **kwargs):
    from brother_ql.backends.helpers import send
    send(instructions=kwargs['instructions'].read(), printer_identifier=ctx.meta.get('PRINTER'), backend_identifier=ctx.meta.get('BACKEND'), blocking=True)

if __name__ == '__main__':
    cli()
