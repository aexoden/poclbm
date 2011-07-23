from datetime import datetime
from threading import RLock
import sys

quiet = False
verbose = False
server = ''
lock = RLock()

TIME_FORMAT = '%d/%m/%Y %H:%M:%S'

def say(format, args=(), say_quiet=False, show_server=True):
    if quiet and not say_quiet: return
    with lock:
        p = format % args
        if verbose:
            print '%s%s,' % (server if show_server else '', datetime.now().strftime(TIME_FORMAT)), p
        else:
            sys.stdout.write('\r%s\r%s%s' % (' '*100, server if show_server else '', p))
        sys.stdout.flush()

def say_line(format, args=(), show_server = True):
    if not verbose:
        format = '%s, %s\n' % (datetime.now().strftime(TIME_FORMAT), format)
    say(format, args, show_server=show_server)
    
def say_quiet(format, args=()):
    say(format, args, True)
