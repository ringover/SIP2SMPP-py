SMPP2SIP-py
===========

This is a first testing version of sip2smpp script. It is only for **testing purpose**. For production, please use the C version.

This script is designed to convert SIP MESSAGE to SMPP, and SMPP to SIP Messages. You can use it to create SMPP gateway to receive or send SMS via/to Sip proxy. 

## CONFIGURATION

Edit Settings on the top of the script

    # Bind Local SIP ADDRESS
    LOCAL_SIP_IP = '127.0.0.1'
    LOCAL_SIP_PORT = 5066

    # SIP DESTINATION	
    DEST_SIP_IP = '127.0.0.1'
    DEST_SIP_PORT = 5061

    # SMPP ESME	
    SMPP_IP = '127.0.0.1'
    SMPP_PORT = '2775'
    SMPP_LOGIN = 'LOGIN'
    SMPP_PASSWORD = 'PASSWORD'

## Start the script

    ./SIP2SMPP
