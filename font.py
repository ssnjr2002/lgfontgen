import logging
import struct
from pathlib import Path
from fontTools import ttLib, subset 

from utils import (
    get_ext, 
    get_basename_wo_ext, 
    sanitise_alphanum
)


logger = logging.getLogger(__name__)


class FontBase:
    """
    Parent class for font file.

    Args:
        font_path (Path): The path to the font file.
    """
    def __init__(self, font_path: Path):
        self.path = font_path
        self.font = ttLib.TTFont(font_path)

    def _get_table(self, table_key):
        table = self.font.get(table_key)
        if table == None:
            raise Exception(f"Could not locate {table_key} table in font: {self.path}")
        
        return table


class FontData(FontBase):
    """
    This class inherits from `FontBase`. It generates the font data
    required for the final apk. 
    
    NOTE: Font data should only be generated after the font is saved 
    or compiled, otherwise the checkSumAdjustment in head table would 
    not match.

    Args:
        font_path (Path): The path to the font file.
    """
    MAGIC_NUM = 0x34234291
    CONSTANT_1 = 0x68796374
    CONSTANT_2 = 0x687969bb

    def __init__(self, font_path):
        super().__init__(font_path)
        self.head = self._get_table("head")
        self.name = self._get_table("name")

    def get_font_data(self) -> bytes:

        magic_num = struct.pack('<I', 0x34234291)
        name_id_1 = self.name.getBestFamilyName().encode('utf-8')
        name_id_1_len = struct.pack('<I', len(name_id_1))
        name_id_2 = self.name.getBestSubFamilyName().encode('utf-8')
        name_id_2_len = struct.pack('<I', len(name_id_2))
        checksum_adj = self.head.checkSumAdjustment
        byteswapped_checksum = struct.pack('<I', checksum_adj)
        byteswapped_checksum_plus_constant = self._uint32_le(
            checksum_adj + FontData.CONSTANT_1
        )
        hash_name_id_1 = self._calc_hash(name_id_1)
        hash_name_id_2 = self._calc_hash(name_id_2)
        combined_hash = self._uint32_le(
            hash_name_id_1 * 2 + hash_name_id_2 + FontData.CONSTANT_2
        )

        # This is the structure of font.dat:
        output = [magic_num]
        output.append(name_id_1_len)
        output.append(name_id_1)
        output.append(name_id_1_len)
        output.append(name_id_1)
        output.append(name_id_2_len)
        output.append(name_id_2)
        output.append(byteswapped_checksum)
        output.append(byteswapped_checksum_plus_constant)
        output.append(combined_hash)
        output.append(name_id_1_len)
        output.append(name_id_1)

        font_data = b''.join(output)
        return font_data
    
    def _calc_hash(self, data_bytes):
        hash = 0x1505
        
        for byte in data_bytes:
            hash = hash * 0x21 + byte
        return hash & 0xffffffff

    def _uint32_le(self, data_hex):
        return struct.pack('<I', data_hex & 0xffffffff)


class FontFile(FontBase):
    """
    This class inherits from `FontBase`. It encapsulates the operations
    to be performed before the font is ready for the apk. 
    
    NOTE: Font data should only be generated after the font is saved, 
    otherwise the checkSumAdjustment in head table would not match.

    Args:
        font_path (Path): The path to the font file.
    """
    FAMILY_ID = 1
    SUBFAM_ID = 2
    MAX_CHARS = 32

    PLATFORM_ID = 3 # windows
    PLATENC_ID = 1 # unicode bmp
    LANG_ID = 1033 # english

    def __init__(self, font_path: Path):
        super().__init__(font_path)

        self.font_file_name = get_basename_wo_ext(font_path)
        self.font_ext = get_ext(font_path)
        self.name = self._get_table("name")
        self.subset_options = None

    def sanitise_name(self):
        family_records = self._locate_name_recs(FontFile.FAMILY_ID)
        subfamily_records = self._locate_name_recs(FontFile.SUBFAM_ID)
        self._setName(family_records, FontFile.FAMILY_ID)
        self._setName(subfamily_records, FontFile.SUBFAM_ID)

    def _locate_name_recs(self, name_id):
        return [rec for rec in self.name.names if rec.nameID == name_id]
    
    def _setName(self, records, id):
        if len(records) == 0:
            sanitised_file_name = sanitise_alphanum(
                self.font_file_name, to_ignore=" "
            )
            cropped_file_name = sanitised_file_name[:FontFile.MAX_CHARS]
            logger.debug(f"Setting NameID {id} to: {cropped_file_name}")
            self.name.setName(
                cropped_file_name, 
                id, 
                FontFile.PLATFORM_ID, 
                FontFile.PLATENC_ID, 
                FontFile.LANG_ID
            )
        else:
            for old_record in records:
                old_name = str(old_record)
                sanitised_font_name = sanitise_alphanum(old_name, to_ignore=" ")
                cropped_font_name = sanitised_font_name[:FontFile.MAX_CHARS]
                logger.debug(f"Changing {old_name} => {cropped_font_name} for NameRecord: ({old_record.nameID}, {old_record.platformID}, {old_record.platEncID}, {old_record.langID})")
                self.name.setName(
                    cropped_font_name, 
                    old_record.nameID, 
                    old_record.platformID, 
                    old_record.platEncID, 
                    old_record.langID
                )
    
    def subset_font(self):
        self.subset_options = subset.Options()
        self.subset_options.layout_features = ["*"]
        self.subset_options.no_subset_tables += ["FFTM"]
        self.subset_options.hinting = False

        subsetter = subset.Subsetter(options=self.subset_options)
        subsetter.populate(
            unicodes=self._character_set(), glyphs=self.font.getGlyphOrder()
        )
        subsetter.subset(self.font)

    def _character_set(self) -> list:
        unicodes = []
        for t in self.font["cmap"].tables:
            if t.isUnicode():
                unicodes.extend(t.cmap.keys())
        return unicodes
    
    def save_to(self, save_path):
        if not self.subset_options:
            self.font.save(save_path)
        else:
            subset.save_font(self.font, save_path, self.subset_options)

    def _get_name(self, from_font):
        logger.debug(f"_get_name: {from_font = }")
        sanitised_file_name = sanitise_alphanum(
            self.font_file_name, to_ignore=" "
        )
        return from_font if from_font is not None else sanitised_file_name

    def get_family(self):
        return self._get_name(self.name.getBestFamilyName())

    def get_subfamily(self):
        return self._get_name(self.name.getBestSubFamilyName())
    
    def get_combined_name(self, sep=""):
        family = self.get_family()
        subfam = self.get_subfamily()

        if family == subfam:
            return family
        
        return family + sep + subfam