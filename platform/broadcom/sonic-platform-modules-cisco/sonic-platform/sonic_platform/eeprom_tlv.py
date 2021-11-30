#############################################################################
# eeprom_tlv.py contains implementation of TLV encoder and decoder
#############################################################################
import os
import sys

try:
    import sys
    import redis
    from sonic_platform_base.sonic_eeprom import eeprom_tlvinfo
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

STATE_DB_INDEX = 6

class Eeprom_Tlv(eeprom_tlvinfo.TlvInfoDecoder):
    #TLV codes
    _TLV_CODE_CISCO_PRODUCT_NAME = eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_PRODUCT_NAME
    _TLV_CODE_CISCO_SERIAL_NUMBER = eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_SERIAL_NUMBER
    _TLV_CODE_CISCO_MAC_BASE = eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_MAC_BASE
    _TLV_CODE_CISCO_MAC_SIZE =eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_MAC_SIZE
    _TLV_CODE_CISCO_PART_NUMBER = eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_PART_NUMBER
    _TLV_CODE_CISCO_PART_REVISION = eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_LABEL_REVISION
    _TLV_CODE_CISCO_HW_REVISION = eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_DEVICE_VERSION
    _TLV_CODE_CISCO_HW_CHANGE_BIT = 0x37
    _TLV_CODE_CISCO_CARD_INDEX = 0x38
    _TLV_CODE_CISCO_MANUF_NAME =eeprom_tlvinfo.TlvInfoDecoder._TLV_CODE_MANUF_NAME

    def cisco_decoder(self, s, t):
        '''
        Return a string representing the contents of the TLV field. The format of
        the string is:
            1. The name of the field left justified in 20 characters
            2. The type code in hex right justified in 5 characters
            3. The length in decimal right justified in 4 characters
            4. The value, left justified in however many characters it takes
        The vailidity of EEPROM contents and the TLV field has been verified
        prior to calling this function. The 's' parameter is unused
        '''
        if t[0] == self._TLV_CODE_CISCO_PRODUCT_NAME:
            name  = "Product Name"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CISCO_SERIAL_NUMBER:
            name  = "Serial Number"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CISCO_PART_NUMBER:
            name = "Part Number"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CISCO_MAC_BASE:
            name = "Base MAC Address"
            value = ":".join(["{:02x}".format(T) for T in t[2:8]]).upper()
        elif t[0] == self._TLV_CODE_PLATFORM_NAME:
            name  = "Platform Name"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CISCO_HW_REVISION:
            name  = "HW_Revision"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CISCO_PART_REVISION:
            name = "Part_Revision"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CISCO_HW_CHANGE_BIT:
            name  = "HW_Change_Bit"
            value = str(t[2])
        elif t[0] == self._TLV_CODE_CISCO_MAC_SIZE:
            name = "MAC Addresses"
            value = str((t[2] << 8) | t[3])
        elif t[0] == self._TLV_CODE_CISCO_MANUF_NAME:
            name = "Manufacturer"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_MANUF_COUNTRY:
            name = "Manufacture Country"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CISCO_CARD_INDEX:
            name = "Card_Index"
            value = t[2:2 + t[1]].decode("ascii")
        elif t[0] == self._TLV_CODE_CRC_32 and len(t) == 6:
            name = "CRC-32"
            value = "0x%08X" % ((t[2] << 24) | (t[3] << 16) | (t[4] << 8) | t[5])
        else:
            name = "Unknown"
            value = ""
            for c in t[2:2 + t[1]]:
                value += "0x%02X " % c
        return name, value


    def cisco_encoder(self, I, v):
        '''
        Validate and encode the string 'v' into the TLV specified by 'I'.
        I[0] is the TLV code.
        '''
        try:
            if I[0] == self._TLV_CODE_CISCO_PRODUCT_NAME   or \
               I[0] == self._TLV_CODE_CISCO_PART_NUMBER    or \
               I[0] == self._TLV_CODE_CISCO_SERIAL_NUMBER  or \
               I[0] == self._TLV_CODE_CISCO_PART_REVISION or \
               I[0] == self._TLV_CODE_PLATFORM_NAME  or \
               I[0] == self._TLV_CODE_CISCO_HW_REVISION   or \
               I[0] == self._TLV_CODE_CISCO_MANUF_NAME     or \
               I[0] == self._TLV_CODE_CISCO_CARD_INDEX:
                errstr = "A string less than 256 characters"
                if len(v) > 255:
                    raise
                value = v.encode("ascii", "replace")
            elif I[0] == self._TLV_CODE_CISCO_HW_CHANGE_BIT:
                errstr  = "A number between 0 and 255"
                num = int(v, 16)
                if num < 0 or num > 255:
                    raise
                value = bytearray([num])
            elif I[0] == self._TLV_CODE_CISCO_MAC_SIZE:
                errstr  = "A number between 0 and 65535"
                num = int(v, 0)
                if num < 0 or num > 65535:
                    raise
                value = bytearray([(num >> 8) & 0xFF, num & 0xFF])
            elif I[0] == self._TLV_CODE_CISCO_MAC_BASE:
                errstr = 'XX:XX:XX:XX:XX:XX'
                mac_digits = v.split(':')
                if len(mac_digits) != 6:
                    raise
                value = bytearray()
                for c in mac_digits:
                    value += bytearray([int(c, 16)])
            elif I[0] == self._TLV_CODE_MANUF_COUNTRY:
                errstr = 'CC, a two character ISO 3166-1 alpha-2 country code'
                if len(v) < 2:
                    raise
                value = v.encode("ascii", "replace")
            elif I[0] == self._TLV_CODE_CRC_32:
                errstr = "CRC"
                value = bytearray()
            else:
                errstr = '0xXX ... A list of space-separated hexidecimal numbers'
                value = bytearray()
                for c in v.split():
                    value += bytearray([int(c, 0)])
        except Exception as inst:
            sys.stderr.write("Error: '" + "0x%02X" % (I[0],) + "' correct format is " + errstr + "\n")
            exit(0)

        return bytearray([I[0]]) + bytearray([len(value)]) + value

    def __print_db(self, db, code, num=0):
        field_name = (db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Name')).decode("ascii")
        if not field_name:
            pass
        else:
            field_len = (db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Len')).decode("ascii")
            field_value = (db.hget('EEPROM_INFO|{}'.format(hex(code)), 'Value')).decode("ascii")
            print("%-20s 0x%02X %3s %s" % (field_name, code, field_len, field_value))

    def helper_read_eeprom(self):
        '''
        Print out the contents of the EEPROM from database
        '''
        client = redis.Redis(db = STATE_DB_INDEX)
        db_state = (client.hget('EEPROM_INFO|State', 'Initialized')).decode('utf8')
        if db_state != '1':
            return -1
        tlv_version = (client.hget('EEPROM_INFO|TlvHeader', 'Version')).decode('utf8')
        if tlv_version:
            print("TlvInfo Header:")
            print("   Id String:    %s" % client.hget('EEPROM_INFO|TlvHeader', 'Id String'))
            print("   Version:      %s" % tlv_version)
            print("   Total Length: %s" % client.hget('EEPROM_INFO|TlvHeader', 'Total Length'))

        print("TLV Name             Code Len Value")
        print("-------------------- ---- --- -----")

        for index in range(self._TLV_CODE_CISCO_PRODUCT_NAME, self._TLV_CODE_CISCO_CARD_INDEX + 1):
            self.__print_db(client, index)

        self.__print_db(client, self._TLV_CODE_CRC_32)

        print("")

        is_valid = (client.hget('EEPROM_INFO|Checksum', 'Valid')).decode('utf8')
        if is_valid != '1':
            print("(*** checksum invalid)")
        else:
            print("(checksum valid)")
        return 0

    def __helper_update(self, e):
        '''
        Decode the contents of the EEPROM and update the contents to database
        '''
        client = redis.Redis(db=STATE_DB_INDEX)
        fvs = {}
        if self._TLV_HDR_ENABLED:
            if not self.is_valid_tlvinfo_header(e):
                print("EEPROM does not contain data in a valid TlvInfo format.")
                return -1
            total_len = (e[9] << 8) | e[10]
            fvs['Id String'] = e[0:7].decode("ascii")
            fvs['Version'] = e[8]
            fvs['Total Length'] = total_len
            client.hmset("EEPROM_INFO|TlvHeader", fvs)
            fvs.clear()
            tlv_index = self._TLV_INFO_HDR_LEN
            tlv_end = self._TLV_INFO_HDR_LEN + total_len
        else:
            tlv_index = self.eeprom_start
            tlv_end = self._TLV_INFO_MAX_LEN

        while (tlv_index + 2) < len(e) and tlv_index < tlv_end:
            if not self.is_valid_tlv(e[tlv_index:]):
                break
            tlv = e[tlv_index:tlv_index + 2 + e[tlv_index + 1]]
            tlv_code = tlv[0]
            fvs['Len'] = tlv[1]
            fvs['Name'], fvs['Value'] = self.cisco_decoder(None, tlv)
            client.hmset('EEPROM_INFO|{}'.format(hex(tlv_code)), fvs)
            fvs.clear()
            if e[tlv_index] == self._TLV_CODE_CRC_32:
                break
            else:
                tlv_index += e[tlv_index + 1] + 2

        (is_valid, valid_crc) = self.is_checksum_valid(e)
        if is_valid:
            fvs['Valid'] = '1'
        else:
            fvs['Valid'] = '0'

        client.hmset('EEPROM_INFO|Checksum', fvs)
        fvs.clear()

        fvs['Initialized'] = '1'
        client.hmset('EEPROM_INFO|State', fvs)
        return 0

    def helper_update_eeprom_db(self, eeprom_code_map):
        '''
        Decode the contents of the EEPROM and update the contents to database
        '''
        new_tlvs = bytearray()
        for key in eeprom_code_map.keys():
            k = key
            v = eeprom_code_map[key].rstrip(' ')
            new_tlv = self.cisco_encoder((k,), v)
            new_tlvs += new_tlv

        if self._TLV_HDR_ENABLED:
            new_tlvs_len = len(new_tlvs) + 6
            new_e = self._TLV_INFO_ID_STRING + bytearray([self._TLV_INFO_VERSION]) + \
                    bytearray([(new_tlvs_len >> 8) & 0xFF]) + \
                    bytearray([new_tlvs_len & 0xFF]) + new_tlvs
        else:
            new_e = new_tlvs

        new_e = new_e + bytearray([self._TLV_CODE_CRC_32]) + bytearray([4])
        new_e += self.encode_checksum(self.calculate_checksum(new_e))
        #print("in helper_update_eeprom_db")
        #self.decode_eeprom(new_e)
        #print("new_e: {}".format(new_e))
        self.__helper_update(new_e)
        #self.helper_read_eeprom()
        return 0
