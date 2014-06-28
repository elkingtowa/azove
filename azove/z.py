import sys
import time
import uuid
import signal
import ConfigParser
from argparse import ArgumentParser
import logging
import logging.config

# this must be called before all other import to enable full qualified import
from common import enable_full_qualified_import
enable_full_qualified_import()

from azove.utils import configure_logging
from azove.utils import data_dir
from azove.utils import sha3
from azove.signals import config_ready
from azove.tcpserver import tcp_server
from azove.peermanager import peer_manager
from azove.apiserver import api_server
from azove.packeter import Packeter


logger = logging.getLogger(__name__)


def create_default_config():
    config = ConfigParser.ConfigParser()
    # set some defaults, which may be overwritten
    config.add_section('network')
    config.set('network', 'listen_host', '0.0.0.0')
    config.set('network', 'listen_port', '30303')
    config.set('network', 'num_peers', '5')
    config.set('network', 'remote_port', '30303')
    config.set('network', 'remote_host', '')
    config.set('network', 'client_id', Packeter.CLIENT_ID)
    config.set('network', 'node_id', sha3(str(uuid.uuid1())).encode('hex'))

    config.add_section('api')
    config.set('api', 'listen_host', '127.0.0.1')
    config.set('api', 'listen_port', '30203')

    config.add_section('misc')
    config.set('misc', 'verbosity', '1')
    config.set('misc', 'config_file', None)
    config.set('misc', 'logging', None)
    config.set('misc', 'data_dir', data_dir.path)
    config.set('misc', 'mining', '10')

    config.add_section('wallet')
    config.set('wallet', 'coinbase', '0' * 40)

    return config


def create_config():
    config = create_default_config()
    parser = ArgumentParser(version=Packeter.CLIENT_ID)
    parser.add_argument(
        "-l", "--listen",
        dest="listen_port",
        default=config.get('network', 'listen_port'),
        help="<port>  Listen on the given port for incoming"
        " connected (default: 30303).")
    parser.add_argument(
        "-a", "--address",
        dest="coinbase",
        help="Set the coinbase (mining payout) address",
        default=config.get('wallet', 'coinbase'))
    parser.add_argument(
        "-d", "--data_dir",
        dest="data_dir",
        help="<path>  Load database from path (default: %s)" % config.get(
            'misc', 'data_dir'),
        default=config.get('misc', 'data_dir'))
    parser.add_argument(
        "-r", "--remote",
        dest="remote_host",
        help="<host> Connect to remote host"
        " (try: 54.201.28.117 or 54.204.10.41)")
    parser.add_argument(
        "-p", "--port",
        dest="remote_port",
        default=config.get('network', 'remote_port'),
        help="<port> Connect to remote port (default: 30303)"
    )
    parser.add_argument(
        "-V", "--verbose",
        dest="verbosity",
        default=config.get('misc', 'verbosity'),
        help="<0 - 3>  Set the log verbosity from 0 to 3 (default: 1)")
    parser.add_argument(
        "-m", "--mining",
        dest="mining",
        default=config.get('misc', 'mining'),
        help="<0 - 100> Percent CPU used for mining 0==off (default: 10)")
    parser.add_argument(
        "-L", "--logging",
        dest="logging",
        default=config.get('misc', 'logging'),
        help="<logger1:LEVEL,logger2:LEVEL> set the console log level for"
        " logger1, logger2, etc. Empty loggername means root-logger,"
        " e.g. 'pyethereum.wire:DEBUG,:INFO'. Overrides '-V'")
    parser.add_argument(
        "-x", "--peers",
        dest="num_peers",
        default=config.get('network', 'num_peers'),
        help="<number> Attempt to connect to given number of peers"
        "(default: 5)")
    parser.add_argument("-C", "--config",
                        dest="config_file",
                        help="read coniguration")

    options = parser.parse_args()

    # set network options
    for attr in ('listen_port', 'remote_host', 'remote_port', 'num_peers'):
        config.set('network', attr, getattr(
            options, attr) or config.get('network', attr))
    # set misc options
    for attr in ('verbosity', 'config_file', 'logging', 'data_dir', 'mining'):
        config.set(
            'misc', attr, getattr(options, attr) or config.get('misc', attr))

    # set wallet options
    for attr in ('coinbase',):
        config.set(
            'wallet', attr, getattr(options, attr) or config.get('wallet', attr))

    if config.get('misc', 'config_file'):
        config.read(config.get('misc', 'config_file'))

    # set datadir
    if config.get('misc', 'data_dir'):
        data_dir.set(config.get('misc', 'data_dir'))

    # configure logging
    configure_logging(
        config.get('misc', 'logging') or '',
        verbosity=config.getint('misc', 'verbosity'))

    return config


def main():
    config = create_config()

    try:
        import pyethereum.monkeypatch
        logger.info("Loaded your customizations from monkeypatch.py")
    except ImportError, e:
        pass

    config_ready.send(sender=None, config=config)
    # import after logger config is ready
    from pyethereum.chainmanager import chain_manager

    try:
        tcp_server.start()
    except IOError as e:
        logger.error("Could not start TCP server: \"{0}\"".format(str(e)))
        sys.exit(1)

    peer_manager.start()
    chain_manager.start()
    api_server.start()

    # handle termination signals
    def signal_handler(signum=None, frame=None):
        logger.info('Signal handler called with signal {0}'.format(signum))
        peer_manager.stop()
        chain_manager.stop()
        tcp_server.stop()

    for sig in [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGINT]:
        signal.signal(sig, signal_handler)

    # connect peer
    if config.get('network', 'remote_host'):
        peer_manager.connect_peer(
            config.get('network', 'remote_host'),
            config.getint('network', 'remote_port'))

    # loop
    while not peer_manager.stopped():
        time.sleep(0.01)

    logger.info('exiting')

    peer_manager.join()

    logger.debug('main thread finished')

if __name__ == '__main__':
    main()
