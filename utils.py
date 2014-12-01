

import fcntl, termios, struct

def get_console_size():
    h, w, hp, wp = struct.unpack("HHHH", 
        fcntl.ioctl(0, termios.TIOCGWINSZ, 
            struct.pack("HHHH", 0, 0, 0, 0)
        )
    )
    return {"height": h, "width": w}

