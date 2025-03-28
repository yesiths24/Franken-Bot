import array
class LSM9DS1:
    WHO_AM_I = const(0xf)
    CTRL_REG1_G = const(0x10)
    INT_GEN_SRC_G = const(0x14)
    OUT_TEMP = const(0x15) # little 2byte
    OUT_G = const(0x18) # little 6byte
    CTRL_REG4_G = const(0x1e)
    
    STATUS_REG = const(0x27)
    OUT_XL = const(0x28) # little 6byte
    FIFO_CTRL_REG = const(0x2e)
    FIFO_SRC = const(0x2f)
    
    OFFSET_REG_X_M = const(0x05) # little 6byte
    CTRL_REG1_M = const(0x20) # 5byte
    OUT_M = const(0x28) # little 6byte
    
    SCALE_GYRO = [(245,0),(500,1),(2000,3)]
    SCALE_ACCEL = [(2,0),(4,2),(8,3),(16,1)]
    
    def __init__(self, i2c, address_gyro=0x6A, address_magnet=0x1C):
        self.i2c = i2c
        self.address_gyro = address_gyro
        self.address_magnet = address_magnet
        # check id's of accelerometer/gyro and magnetometer
        if (self.read_id_magnet() != b'=') or (self.read_id_gyro() != b'h'):
            raise OSError("Invalid LSM9DS1 device, using address {}/{}".format(
                    address_gyro,address_magnet))
        # allocate scratch buffer for efficient conversions and memread op's
        self.scratch = array.array('B',[0,0,0,0,0,0])
        self.init_gyro_accel()
        self.init_magnetometer()
        
    def init_gyro_accel(self, sample_rate=6, scale_gyro=0, scale_accel=0):
        """ Initalizes Gyro and Accelerator.
        sample rate: 0-6 (off, 14.9Hz, 59.5Hz, 119Hz, 238Hz, 476Hz, 952Hz)
        scale_gyro: 0-2 (245dps, 500dps, 2000dps ) 
        scale_accel: 0-3 (+/-2g, +/-4g, +/-8g, +-16g)
        """
        assert sample_rate <= 6, "invalid sampling rate: %d" % sample_rate
        assert scale_gyro <= 2, "invalid gyro scaling: %d" % scale_gyro
        assert scale_accel <= 3, "invalid accelerometer scaling: %d" % scale_accel
        
        i2c = self.i2c
        self.i2c.addr = self.address_gyro
        mv = memoryview(self.scratch)        
        # angular control registers 1-3 / Orientation
        mv[0] = ((sample_rate & 0x07) << 5) | ((self.SCALE_GYRO[scale_gyro][1] & 0x3) << 3) 
        mv[1:4] = b'\x00\x00\x00'
#        i2c.write_mem_list(CTRL_REG1_G, mv[:5], 5)
        for i in range(5):
          i2c.write_u8(CTRL_REG1_G+i, mv[i])
        # ctrl4 - enable x,y,z, outputs, no irq latching, no 4D
        # ctrl5 - enable all axes, no decimation
        # ctrl6 - set scaling and sample rate of accel 
        # ctrl7,8 - leave at default values
        # ctrl9 - FIFO enabled
        mv[0] = mv[1] = 0x38
        mv[2] = ((sample_rate & 7) << 5) | ((self.SCALE_ACCEL[scale_accel][1] & 0x3) << 3)
        mv[3] = 0x00
        mv[4] = 0x4
        mv[5] = 0x2
#        i2c.write_mem_list(CTRL_REG4_G, mv[:6], 6)
        for i in range(6):
          i2c.write_u8(CTRL_REG4_G+i, mv[i])

        # fifo: use continous mode (overwrite old data if overflow)
        i2c.write_u8(FIFO_CTRL_REG, 0x00)
        i2c.write_u8(FIFO_CTRL_REG, 0xC0)

        self.scale_gyro = 32768 / self.SCALE_GYRO[scale_gyro][0]
        self.scale_accel = 32768 / self.SCALE_ACCEL[scale_accel][0]
        
    def init_magnetometer(self, sample_rate=7, scale_magnet=0):
        """ 
        sample rates = 0-7 (0.625, 1.25, 2.5, 5, 10, 20, 40, 80Hz)
        scaling = 0-3 (+/-4, +/-8, +/-12, +/-16 Gauss)
        """
        assert sample_rate < 8, "invalid sample rate: %d (0-7)" % sample_rate
        assert scale_magnet < 4, "invalid scaling: %d (0-3)" % scale_magnet
        i2c = self.i2c
        self.i2c.addr = self.address_magnet
        mv = memoryview(self.scratch)       
        mv[0] = 0x40 | (sample_rate << 2) # ctrl1: high performance mode
        mv[1] = scale_magnet << 5 # ctrl2: scale, normal mode, no reset
        mv[2] = 0x00 # ctrl3: continous conversion, no low power, I2C
        mv[3] = 0x08 # ctrl4: high performance z-axis
        mv[4] = 0x00 # ctr5: no fast read, no block update
#        i2c.write_mem_list(CTRL_REG1_M, mv[:5], 5)
        for i in range(5):
          i2c.write_u8(CTRL_REG1_M+i, mv[i])
        self.scale_factor_magnet = 32768 / ((scale_magnet+1) * 4 )
        
    def calibrate_magnet(self, offset):
        """ 
        offset is a magnet vecor that will be substracted by the magnetometer
        for each measurement. It is written to the magnetometer's offset register
        """
        i2c = self.i2c
        self.i2c.addr = self.address_magnet
        offset = [int(i*self.scale_factor_magnet) for i in offset]
        mv = memoryview(self.scratch) 
        mv[0] = offset[0] & 0xff
        mv[1] = offset[0] >> 8
        mv[2] = offset[1] & 0xff
        mv[3] = offset[1] >> 8
        mv[4] = offset[2] & 0xff
        mv[5] = offset[2] >> 8
        self.i2c.write_mem_list(OFFSET_REG_X_M, mv[:6], 6)
                
    def read_id_gyro(self):
        i2c = self.i2c
        self.i2c.addr = self.address_gyro
        return self.i2c.read_reg(WHO_AM_I, 1)

    def read_id_magnet(self):
        i2c = self.i2c
        self.i2c.addr = self.address_magnet
        return self.i2c.read_reg(WHO_AM_I, 1)
                        
    def read_magnet(self):
        """Returns magnetometer vector in gauss.
        raw_values: if True, the non-scaled adc values are returned
        """
        i2c = self.i2c
        self.i2c.addr = self.address_magnet
        f = self.scale_factor_magnet
        out = self.i2c.read_mem_data(OUT_M, 3, 2) #i2c_bus.INT16LE
        return (out[0]/f, out[1]/f, out[2]/f)
    
    def read_gyro(self):
        """Returns gyroscope vector in degrees/sec."""
        i2c = self.i2c
        self.i2c.addr = self.address_gyro
        f = self.scale_gyro
        out = self.i2c.read_mem_data(OUT_G, 3, 2) #i2c_bus.INT16LE
        return (out[0]/f, out[1]/f, out[2]/f)
    
    def read_accel(self):
        """Returns acceleration vector in gravity units (9.81m/s^2)."""
        i2c = self.i2c
        self.i2c.addr = self.address_gyro
        f = self.scale_accel
        out = self.i2c.read_mem_data(OUT_XL, 3, 2) #i2c_bus.INT16LE
        return (out[0]/f, out[1]/f, out[2]/f)