"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, October 19th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import sys
from acmd import io

def main(argv, default_port=1200):
    if len(argv) == 1:
        raise RuntimeError('Not enough arguments specified!')

    if argv[1] == '--server':
        if len(argv) <= 2:
            raise RuntimeError('Server argument requires a address <127.0.0.0>!')

        factory = io.NetworkIOFactory(argv[2], default_port, io.NetworkIOHandler)
        factory.run()
    elif argv[1] == '--client':
        if len(argv) <= 2:
            raise RuntimeError('Client argument requires a connection address <127.0.0.0>!')

        connector = io.NetworkIOConnector(argv[2], default_port)
        connector.run()

    # exit the program cleanly, no errors...
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)
