
"""
Handle I2C serial communication through Ft4222.

Does not offer support for toggling RESET and BOOT0.
"""

import ft4222
import ft4222.I2CMaster

nb_reply_subframes_per_cmd={
    0x00 : 1+3,
    0x02 : 1+2,
}

class I2cFt4222Connection:
    """Wrap a ft4222.openBy... connection """

    def __init__(self, i2c_ft4222_port, i2c_frequency=400000, i2c_slave_addr=0x00):
        """Construct a I2cFt4222Connection (not yet connected).
            i2c_ft4222_port : string with format "FT4222_I2C:[<location>]:[<i2c_addr>]"
                with <location> = location value returned by ft4222.getDeviceInfoDetail()
                                  if location is not specified, use first FT4222 interface found
                with <i2c_addr> = I2C address of bootloader
                                  if I2C address is not specified, scan I2C bus for valid bootlaoder respons
        """
        self.i2c_ft4222_port = i2c_ft4222_port
        self.i2c_backend=True
        self.i2c_frequency = i2c_frequency
        self.slave_addr = i2c_slave_addr
        
        # not used but kept for compatibility with uart interface
        # self.baud_rate = baud_rate
        # self.parity = parity

        # not used but kept for compatibility with uart interface
        # self.swap_rts_dtr = False
        # self.reset_active_high = False
        # self.boot0_active_low = False

        # don't connect yet; caller should use connect() separately
        self.i2c_connection = None

        self._timeout = 5

    @property
    def timeout(self):
        """Get timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Set timeout (seconds)."""
        self._timeout = timeout
        self.i2c_connection.setTimeouts(timeout*1000.0, timeout*1000.0)

    def connect(self):
        """Connect to the FT4222 I2C port."""
        # if requested, display list of FT4222 peripherals
        if self.i2c_ft4222_port=="FT4222_I2C:?":
            nb = ft4222.createDeviceInfoList()
            print("List of available FT4222_I2C interfaces:")
            for i in range(0,nb):
                dev = ft4222.getDeviceInfoDetail(devnum=i, update=False)
                if dev['description']==b'FT4222 A':
                    print(f" - {dev['description'].decode('utf-8')} : id = {dev['location']}")
            raise IOError()

        tmp = self.i2c_ft4222_port + "::"
        intf = tmp.split(':')
        if len(intf[1])==0:
            # location not specified, use first matching interface
            intf_type = 'description'
            i2c_intf_id = 'FT4222 A'
            print(f"Using FT4222 interface discovery")
        else:
            intf_type='location'
            i2c_intf_id=int(intf[1])
            print(f"Using specified FT4222 interface at location={i2c_intf_id}")
            
        if len(intf[2])==0:
            # I2C address not specified, will scan for valid bootlaoder response
            self.slave_addr = 0x00
        else:
            self.slave_addr = int(intf[2], 0)
            print(f"Using specified I2C address = 0x{self.slave_addr:02X}")
            
        if intf_type=="description":
            self.i2c_connection = ft4222.openByDescription(i2c_intf_id)
        if intf_type=="location":
            self.i2c_connection = ft4222.openByLocation(i2c_intf_id)
            
        # configure I2C
        self.timeout = 1000
        self.i2c_connection.i2cMaster_Init(int(self.i2c_frequency/1000))
        
        # scan to discover slave peripheral I2C address
        # returns first device that respond with data=NACK byte (0x1F)
        if self.slave_addr == 0x00:
            for i2c_addr in range(0x01, 0x7F):
                data = self.i2c_connection.i2cMaster_ReadEx(i2c_addr, ft4222.I2CMaster.Flag.START_AND_STOP, 1)
                sts = self.i2c_connection.i2cMaster_GetStatus()
                if ( not sts & ft4222.I2CMaster.ControllerStatus.ADDRESS_NACK ) and ( data==b'\x1f' ):
                    self.slave_addr = i2c_addr
                    print(f"Using discovered I2C address = 0x{self.slave_addr:02X}")
                    break
        if self.slave_addr == 0x00:
            raise IOError("I2C bus scan failed. Is bootloader activated (boot0 + nrst) ?")
            
    def disconnect(self):
        """Close the connection."""
        if not self.i2c_connection:
            return

        self.i2c_connection.close()
        self.i2c_connection = None

    def write(self, data):
        """ I2C WRITE transaction
            data     : list of bytes to write
        """
        out = bytes(data)
        self.i2c_connection.i2cMaster_WriteEx(self.slave_addr, ft4222.I2CMaster.Flag.START_AND_STOP, out)
        
    def read(self, nb_bytes=1, subframe=None):
        """ I2C READ transaction
            nb_bytes : number of bytes to read
        """
        # manage I2C START and STOP conditions in case an I2C frame is split over
        # several read() calls (needed for GET and GET_ID commands, cf bootloader.py
        if subframe=='first':
            flags = ft4222.I2CMaster.Flag.START
        elif subframe=='middle':
            flags = ft4222.I2CMaster.Flag.NONE
        elif subframe=='last':
            flags = ft4222.I2CMaster.Flag.STOP
        else:
            flags = ft4222.I2CMaster.Flag.START_AND_STOP
            
        data = self.i2c_connection.i2cMaster_ReadEx(self.slave_addr, flags, nb_bytes)
        return data

    def enable_reset(self, enable=True):
        """Enable or disable the reset IO line."""
        # not implemented
        pass

    def enable_boot0(self, enable=True):
        """Enable or disable the boot0 IO line."""
        # not implemented
        pass

    def flush_imput_buffer(self):
        """Flush the input buffer to remove any stale read data."""
        # not implemented
        pass
