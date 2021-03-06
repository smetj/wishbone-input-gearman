::

              __       __    __
    .--.--.--|__.-----|  |--|  |--.-----.-----.-----.
    |  |  |  |  |__ --|     |  _  |  _  |     |  -__|
    |________|__|_____|__|__|_____|_____|__|__|_____|
                                       version 2.3.3

    Build composable event pipeline servers with minimal effort.



    ======================
    wishbone.input.gearman
    ======================

    Version: 1.2.1

    Consumes events/jobs from  Gearmand.
    ------------------------------------


        Consumes jobs from a Gearmand server.
        When secret is none, no decryption is done.


        Parameters:

            - hostlist(list)(["localhost:4730"])
               |  A list of gearmand servers.  Each entry should have
               |  format host:port.

            - secret(str)(None)
               |  The AES encryption key to decrypt Mod_gearman messages.

            - workers(int)(1)
               |  The number of gearman workers within 1 process.

            - queue(str)(wishbone)
               |  The queue to consume jobs from.

            - enable_keepalive(bool)(False)
               |  Attempt to monkey patch the gearmand module to enable socket
               |  keepalive.


        Queues:

            - outbox:   Outgoing events.


