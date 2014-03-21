"""SMPP client module"""

import socket
import struct
import binascii
import time
import logging

import smpp
import pdu
import command


SMPP_CLIENT_STATE_CLOSED = 0
SMPP_CLIENT_STATE_OPEN = 1
SMPP_CLIENT_STATE_BOUND_TX = 2
SMPP_CLIENT_STATE_BOUND_RX = 3
SMPP_CLIENT_STATE_BOUND_TRX = 4


command_states = {
    'bind_transmitter': (SMPP_CLIENT_STATE_OPEN,),
    'bind_transmitter_resp': (SMPP_CLIENT_STATE_OPEN,),
    'bind_receiver': (SMPP_CLIENT_STATE_OPEN,),
    'bind_receiver_resp': (SMPP_CLIENT_STATE_OPEN,),
    'bind_transceiver': (SMPP_CLIENT_STATE_OPEN,),
    'bind_transceiver_resp': (SMPP_CLIENT_STATE_OPEN,),
    'outbind': (SMPP_CLIENT_STATE_OPEN,),
    'unbind': (SMPP_CLIENT_STATE_BOUND_TX,
               SMPP_CLIENT_STATE_BOUND_RX,
               SMPP_CLIENT_STATE_BOUND_TRX,),
    'unbind_resp': (SMPP_CLIENT_STATE_BOUND_TX,
                    SMPP_CLIENT_STATE_BOUND_RX,
                    SMPP_CLIENT_STATE_BOUND_TRX,),
    'submit_sm': (SMPP_CLIENT_STATE_BOUND_TX,
                  SMPP_CLIENT_STATE_BOUND_TRX,),
    'submit_sm_resp': (SMPP_CLIENT_STATE_BOUND_TX,
                       SMPP_CLIENT_STATE_BOUND_TRX,),
    'submit_sm_multi': (SMPP_CLIENT_STATE_BOUND_TX,
                        SMPP_CLIENT_STATE_BOUND_TRX,),
    'submit_sm_multi_resp': (SMPP_CLIENT_STATE_BOUND_TX,
                             SMPP_CLIENT_STATE_BOUND_TRX,),
    'data_sm': (SMPP_CLIENT_STATE_BOUND_TX,
                SMPP_CLIENT_STATE_BOUND_RX,
                SMPP_CLIENT_STATE_BOUND_TRX,),
    'data_sm_resp': (SMPP_CLIENT_STATE_BOUND_TX,
                     SMPP_CLIENT_STATE_BOUND_RX,
                     SMPP_CLIENT_STATE_BOUND_TRX,),
    'deliver_sm': (SMPP_CLIENT_STATE_BOUND_RX,
                   SMPP_CLIENT_STATE_BOUND_TRX,),
    'deliver_sm_resp': (SMPP_CLIENT_STATE_BOUND_RX,
                        SMPP_CLIENT_STATE_BOUND_TRX,),
    'query_sm': (SMPP_CLIENT_STATE_BOUND_RX,
                 SMPP_CLIENT_STATE_BOUND_TRX,),
    'query_sm_resp': (SMPP_CLIENT_STATE_BOUND_RX,
                      SMPP_CLIENT_STATE_BOUND_TRX,),
    'cancel_sm': (SMPP_CLIENT_STATE_BOUND_RX,
                  SMPP_CLIENT_STATE_BOUND_TRX,),
    'cancel_sm_resp': (SMPP_CLIENT_STATE_BOUND_RX,
                       SMPP_CLIENT_STATE_BOUND_TRX,),
    'replace_sm': (SMPP_CLIENT_STATE_BOUND_TX,),
    'replace_sm_resp': (SMPP_CLIENT_STATE_BOUND_TX,),
    'enquire_link': (SMPP_CLIENT_STATE_BOUND_TX,
                     SMPP_CLIENT_STATE_BOUND_RX,
                     SMPP_CLIENT_STATE_BOUND_TRX,),
    'enquire_link_resp': (SMPP_CLIENT_STATE_BOUND_TX,
                          SMPP_CLIENT_STATE_BOUND_RX,
                          SMPP_CLIENT_STATE_BOUND_TRX,),
    'generic_nack': (SMPP_CLIENT_STATE_BOUND_TX,
                     SMPP_CLIENT_STATE_BOUND_RX,
                     SMPP_CLIENT_STATE_BOUND_TRX,)
}

state_setters = {
    'bind_transmitter_resp': SMPP_CLIENT_STATE_BOUND_TX,
    'bind_receiver_resp': SMPP_CLIENT_STATE_BOUND_RX,
    'bind_transceiver_resp': SMPP_CLIENT_STATE_BOUND_TRX,
    'unbind_resp': SMPP_CLIENT_STATE_OPEN
}

#
# Global response number
#
responses = 0

logger    = logging.getLogger('smpplib.client')


class Client:
    """SMPP client class"""

    state = SMPP_CLIENT_STATE_CLOSED

    host = None
    port = None
    vendor = None
    _socket = None

    _stack = []  # PDU stack
    _error_stack = None


    def __init__(self, host, port):
        """Initialize"""

        self.host = host
        self.port = int(port)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(1)
        self._error_stack = []
        self.receiver_mode = False


    def connect(self):
        """Connect to SMSC"""

        logger.info('Connecting to %s:%s...' % (self.host, self.port))

        try:
            self._socket.connect((self.host, self.port))
            self.state = SMPP_CLIENT_STATE_OPEN
        except socket.error:
            raise ConnectionError("Connection refused")


    def disconnect(self):
        """Disconnect from the SMSC"""
        
        logger.info('Disconnecting...')

        self._socket.close()
        self.state = SMPP_CLIENT_STATE_CLOSED


    def _bind(self, command_name, **args):
        """Send bind_transmitter command to the SMSC"""

        if command_name in ['bind_receiver', 'bind_transceiver']:
            self.receiver_mode = True

        #smppinst = smpp.get_instance()
        p = smpp.make_pdu(command_name, **(args))
        
        res = self.send_pdu(p)
        return self.read_pdu()


    def bind_transmitter(self, **args):
        """Bind as a transmitter"""

        return self._bind('bind_transmitter', **(args))

        
    def bind_receiver(self, **args):
        """Bind as a receiver"""

        return self._bind('bind_receiver', **(args))

        
    def bind_transceiver(self, **args):
        """Bind as a transmitter and receiver at once"""

        return self._bind('bind_transceiver', **(args))


    def unbind(self):
        """Unbind from the SMSC"""

        #smppinst = smpp.get_instance()
        p = smpp.make_pdu('unbind')

        res = self.send_pdu(p)
        return self.read_pdu()


    def send_pdu(self, p):
        """Send PDU to the SMSC"""

        if not self.state in command_states[p.command]:
            raise Exception("Command %s failed: %s" \
                % (p.command, pdu.descs[pdu.SMPP_ESME_RINVBNDSTS]))

        self._push_pdu(p)
        logger.debug('Sending %s PDU' % (p.command))

        generated = p.generate()

        logger.debug('>> ' + binascii.b2a_hex(generated) + " " + str(len(generated)) + ' bytes')
        res = self._socket.send(generated)

        return True


    def read_pdu(self):
        """Read PDU from the SMSC"""

        logger.debug('Waiting for PDU...')

        raw_len = self._socket.recv(4)
        if raw_len == 0:
            return False
	
#	import pdb
#	pdb.set_trace()

        try:
            length = struct.unpack('>L', raw_len)[0]
        except struct.error:
            #raise ConnectionError("Connection to server lost")
            logger.error('Receive broken pdu...')
            return False
        raw_pdu = self._socket.recv(length - 4)
        raw_pdu = raw_len + raw_pdu

        logger.debug('<< ' + binascii.b2a_hex(raw_pdu) + str(len(raw_pdu)) + ' bytes')

        cmd = pdu.PDU.extract_command(raw_pdu)

	if cmd is None:
	    return False

        logger.debug('Read %s PDU' % cmd)
        
	p = smpp.parse_pdu(raw_pdu)
        self._push_pdu(p)

        if p.is_error():
            raise Exception('(%s) %s: %s' % (p.status, p.command,
                pdu.descs[p.status]))
        elif p.command in state_setters.keys():
            self.state = state_setters[p.command]

        return p


    def accept(self, object):
        """Accept an object"""

        raise NotImplementedError('not implemented')


    def _message_received(self, p):
        """Handler for received message event"""
        dsmr = smpp.make_pdu('deliver_sm_resp')#, message_id=args['pdu'].sm_default_msg_id)
        dsmr.sequence = p.sequence
        self.send_pdu(dsmr)
        self.message_received_handler(pdu=p)

    def _enquire_link_received(self):
        ler = smpp.make_pdu('enquire_link_resp')#, message_id=args['pdu'].sm_default_msg_id)
        self.send_pdu(ler)
        logger.info("Link Enuiry...")
        
    def set_message_received_handler(self, func):
        """Set new function to handle message receive event"""

        self.message_received_handler = func


    @staticmethod
    def message_received_handler(**args):
        """Custom handler to process received message. May be overridden"""

        logger.info('Message received handler (shoud be overridden)')
    
        
    def listen(self):
        """Listen for PDUs and act"""

        if not self.receiver_mode:
            raise Exception('Client.listen() is not allowed to be ' \
                'invoked manually for non receiver connection')

        while True:
	    time.sleep(0.01)
            try:
                p = self.read_pdu()
            except socket.timeout:
                logger.debug('Socket timeout, listening again')
                continue
	    if p is False:
		continue

            if p.command == 'unbind': #unbind_res
                logger.info('Unbind command received')
                break
            elif p.command == 'deliver_sm':
                self._message_received(p)
            elif p.command == 'enquire_link':
                self._enquire_link_received()
            else:
                logger.warning("Unhandled SMPP command '%s'", p.command)
                


    def send_message(self, **args):
        """Send message
        
        Required Arguments:
            source_addr_ton -- Source address TON
            source_addr -- Source address (string)
            dest_addr_ton -- Destination address TON
            destination_addr -- Destination address (string)
            short_message -- Message text (string)"""

        ssm = smpp.make_pdu('submit_sm', **(args))

        self.send_pdu(ssm)
        resp = self.read_pdu()

        return resp


    def _push_pdu(self, p):
        """Push PDU into a stack"""
        
        if p.is_request():
            k = 'request'
        else:
            k = 'response'

        self._stack.append({p.sequence: {k: p}})


class ConnectionError(Exception):
    """Connection error"""

