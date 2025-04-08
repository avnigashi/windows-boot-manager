import os
import sys
import re
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from tkinter.font import Font
import json
import datetime
import uuid
import threading
import time
import locale

class AdvancedBootManager:
    def __init__(self):
       
        if not self.is_admin():
            print("This script requires administrator privileges.")
            sys.exit(1)
        
       
        self.entries_cache = {}
        self.default_entry = None
        
       
        self.system_locale = locale.getlocale()[0]
        print(f"System locale: {self.system_locale}")
        
       
        self.property_translations = {
           
            'en': {
                'identifier': 'identifier',
                'device': 'device',
                'path': 'path',
                'description': 'description',
                'type': 'type',
                'default': 'default',
                'bootmgr': 'bootmgr',
                'timeout': 'timeout',
                'displayorder': 'displayorder',
                'osdevice': 'osdevice'
            },
           
            'de': {
                'identifier': 'bezeichner',
                'device': 'gerät',
                'path': 'pfad',
                'description': 'beschreibung',
                'type': 'typ',
                'default': 'standard',
                'bootmgr': 'boot-manager',
                'timeout': 'zeitlimit',
                'displayorder': 'anzeigereihenfolge',
                'osdevice': 'osgerät'
            },
           
            'fr': {
                'identifier': 'identificateur',
                'device': 'périphérique',
                'path': 'chemin',
                'description': 'description',
                'type': 'type',
                'default': 'défaut',
                'bootmgr': 'gestionnaire de démarrage',
                'timeout': 'délai d\'attente',
                'displayorder': 'ordre d\'affichage',
                'osdevice': 'périphérique os'
            },
           
            'es': {
                'identifier': 'identificador',
                'device': 'dispositivo',
                'path': 'ruta',
                'description': 'descripción',
                'type': 'tipo',
                'default': 'predeterminado',
                'bootmgr': 'administrador de arranque',
                'timeout': 'tiempo de espera',
                'displayorder': 'orden de visualización',
                'osdevice': 'dispositivo del so'
            }
        }
        
       
        self.lang_code = 'en' 
        if self.system_locale:
            for code in self.property_translations.keys():
                if self.system_locale.startswith(code):
                    self.lang_code = code
                    break
        
        print(f"Using language code: {self.lang_code} for parsing")
    
    def is_admin(self):
        """Check if the script is running with administrator privileges"""
        try:
            return os.getuid() == 0 
        except AttributeError:
           
            try:
                return subprocess.check_call(["net", "session"],
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL) == 0
            except subprocess.CalledProcessError:
                return False
    
    def get_translation(self, key):
        """Get the translated version of a property key"""
        try:
            return self.property_translations[self.lang_code][key.lower()]
        except (KeyError, AttributeError):
            return key
    
    def get_entries(self):
        """Get all boot entries directly as formatted text"""
        try:
            result = subprocess.run(["bcdedit", "/enum", "/v"],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode != 0:
                print(f"Error: bcdedit command failed with code {result.returncode}")
                print(f"Error message: {result.stderr}")
                return None
            return result.stdout
        except Exception as e:
            print(f"Error executing bcdedit: {e}")
            return None
    
    def get_entry_types(self):
        """Get all types of boot entries available"""
        try:
            result = subprocess.run(["bcdedit", "/enum", "all"],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode != 0:
                return []
            types = set()
            type_key = self.get_translation("type").lower()
            for line in result.stdout.split('\n'):
                if type_key in line.lower():
                    parts = line.split()
                    if len(parts) > 1:
                        type_value = parts[-1]
                        types.add(type_value)
            return list(types)
        except Exception as e:
            print(f"Error getting entry types: {e}")
            return []
    
    def list_identifiers(self):
        """Extract all entry identifiers from bcdedit output"""
        output = self.get_entries()
        if not output:
            return []
        identifiers = re.findall(r'{[a-fA-F0-9\-]+}', output)
        unique_identifiers = []
        for id in identifiers:
            if id not in unique_identifiers:
                unique_identifiers.append(id)
        return unique_identifiers
    
    def get_entry_info(self, identifier):
        """Get detailed information for a specific boot entry"""
        try:
            result = subprocess.run(["bcdedit", "/enum", identifier, "/v"],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode != 0:
                print(f"Error getting entry info: {result.stderr}")
                return None
            return result.stdout
        except Exception as e:
            print(f"Error executing bcdedit: {e}")
            return None
    
    def parse_entry_properties(self, entry_info):
        """Parse entry properties in a language-agnostic way"""
        if not entry_info:
            return {}
        properties = {}
        pattern = r'^\s*([^\s]+)\s+(.+)$'
        for line in entry_info.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                key = match.group(1).lower()
                value = match.group(2).strip()
                properties[key] = value
        id_match = re.search(r'({[a-fA-F0-9\-]+})', entry_info)
        if id_match:
            properties['identifier'] = id_match.group(1)
        return properties
    
    def get_entry_description(self, identifier):
        """Get the description of a boot entry"""
        info = self.get_entry_info(identifier)
        if not info:
            return "Unknown"
        desc_key = self.get_translation("description").lower()
        pattern = rf'{desc_key}\s+(.+)'
        match = re.search(pattern, info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'description\s+(.+)', info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        properties = self.parse_entry_properties(info)
        for key, value in properties.items():
            if 'description' in key.lower() or desc_key in key.lower():
                return value
        return "Unknown"
    
    def get_entry_device(self, identifier):
        """Get the device of a boot entry"""
        info = self.get_entry_info(identifier)
        if not info:
            return ""
        device_key = self.get_translation("device").lower()
        osdevice_key = self.get_translation("osdevice").lower()
        pattern = rf'{device_key}\s+(.+)'
        match = re.search(pattern, info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        pattern = rf'{osdevice_key}\s+(.+)'
        match = re.search(pattern, info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        properties = self.parse_entry_properties(info)
        for key, value in properties.items():
            if 'device' in key.lower() or device_key in key.lower():
                return value
            elif 'osdevice' in key.lower() or osdevice_key in key.lower():
                return value
        return ""
    
    def get_entry_path(self, identifier):
        """Get the path of a boot entry"""
        info = self.get_entry_info(identifier)
        if not info:
            return ""
        path_key = self.get_translation("path").lower()
        pattern = rf'{path_key}\s+(.+)'
        match = re.search(pattern, info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'path\s+(.+)', info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        properties = self.parse_entry_properties(info)
        for key, value in properties.items():
            if 'path' in key.lower() or path_key in key.lower():
                return value
        return ""
    
    def get_entry_type(self, identifier):
        """Get the type of a boot entry"""
        info = self.get_entry_info(identifier)
        if not info:
            return "Unknown"
        type_key = self.get_translation("type").lower()
        pattern = rf'{type_key}\s+(.+)'
        match = re.search(pattern, info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match = re.search(r'type\s+(.+)', info, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        properties = self.parse_entry_properties(info)
        for key, value in properties.items():
            if 'type' in key.lower() or type_key in key.lower():
                return value
        return "Unknown"
    
    def check_ramdisk(self, identifier):
        """Check if a boot entry has ramdisk configuration"""
        entry_info = self.get_entry_info(identifier)
        if not entry_info:
            return False
        return any(param in entry_info.lower() for param in ['ramdisksdidevice', 'ramdisksdipath', 'ramdisksdiprocessorarchitecture'])
    
    def check_uefi(self, identifier):
        """Check if a boot entry is for UEFI boot"""
        entry_info = self.get_entry_info(identifier)
        if not entry_info:
            return False
        return '.efi' in entry_info.lower() or 'uefi' in entry_info.lower()
    
    def partition_exists(self, device):
        """
        Check if the partition specified in the device string exists.
        The expected device string is in the format "partition=C:".
        """
        try:
            if device and device.lower().startswith("partition="):
                partition = device.split("=", 1)[1]
                if not partition.endswith("\\"):
                    partition = partition + "\\"
                return os.path.exists(partition)
            return True
        except Exception as e:
            print(f"Error checking partition existence: {e}")
            return False
    
    def has_missing_path_or_device(self, identifier):
        """
        Check if a boot entry is missing path or device, or if its specified partition does not exist.
        """
        device = self.get_entry_device(identifier)
        path = self.get_entry_path(identifier)
        if not device or not path or device.lower() == "unknown" or path.lower() == "unknown":
            return True
        if device.lower().startswith("partition=") and not self.partition_exists(device):
            return True
        return False
    
    def get_default_entry(self):
        """Get the default boot entry identifier"""
        try:
            bootmgr_term = self.get_translation("bootmgr").lower()
            result = subprocess.run(["bcdedit", "/enum", "{bootmgr}"],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode == 0:
                default_key = self.get_translation("default").lower()
                pattern = rf'{default_key}\s+({{\w+-\w+-\w+-\w+-\w+}})'
                match = re.search(pattern, result.stdout, re.IGNORECASE)
                if match:
                    self.default_entry = match.group(1)
                    return self.default_entry
            all_entries = self.get_entries()
            if all_entries:
                sections = re.split(r'\n\n+', all_entries)
                bootmgr_section = None
                for section in sections:
                    if bootmgr_term in section.lower() or "bootmgr" in section.lower():
                        bootmgr_section = section
                        break
                if bootmgr_section:
                    default_key = self.get_translation("default").lower()
                    pattern = rf'{default_key}\s+({{\w+-\w+-\w+-\w+-\w+}})'
                    match = re.search(pattern, bootmgr_section, re.IGNORECASE)
                    if match:
                        self.default_entry = match.group(1)
                        return self.default_entry
            return None
        except Exception as e:
            print(f"Error getting default entry: {e}")
            return None
    
    def get_display_order(self):
        """Get the display order of boot entries"""
        try:
            result = subprocess.run(["bcdedit", "/enum", "{bootmgr}"],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode != 0:
                return []
            displayorder_key = self.get_translation("displayorder").lower()
            display_order = []
            display_section = False
            for line in result.stdout.split('\n'):
                if displayorder_key in line.lower() or "displayorder" in line.lower():
                    display_section = True
                    match = re.search(r'({[a-fA-F0-9\-]+})', line)
                    if match:
                        display_order.append(match.group(1))
                elif display_section and line.strip():
                    match = re.search(r'({[a-fA-F0-9\-]+})', line)
                    if match:
                        display_order.append(match.group(1))
                elif display_section and not line.strip():
                    display_section = False
            return display_order
        except Exception as e:
            print(f"Error getting display order: {e}")
            return []
    
    def set_display_order(self, order_list):
        """Set the display order of boot entries"""
        try:
            subprocess.run(["bcdedit", "/deletevalue", "{bootmgr}", "displayorder"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            if order_list:
                cmd = ["bcdedit", "/displayorder"]
                cmd.extend(order_list)
                result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
                return result.returncode == 0
            return True
        except Exception as e:
            print(f"Error setting display order: {e}")
            return False
    
    def move_entry_up(self, identifier):
        """Move a boot entry up in the display order"""
        display_order = self.get_display_order()
        if not display_order or identifier not in display_order:
            return False
        index = display_order.index(identifier)
        if index == 0:
            return True
        display_order[index], display_order[index-1] = display_order[index-1], display_order[index]
        return self.set_display_order(display_order)
    
    def move_entry_down(self, identifier):
        """Move a boot entry down in the display order"""
        display_order = self.get_display_order()
        if not display_order or identifier not in display_order:
            return False
        index = display_order.index(identifier)
        if index == len(display_order) - 1:
            return True
        display_order[index], display_order[index+1] = display_order[index+1], display_order[index]
        return self.set_display_order(display_order)
    
    def set_default_entry(self, identifier):
        """Set the default boot entry"""
        try:
            result = subprocess.run(["bcdedit", "/default", identifier],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode == 0:
                self.default_entry = identifier
                return True
            return False
        except Exception as e:
            print(f"Error setting default entry: {e}")
            return False
    
    def set_timeout(self, seconds):
        """Set the boot menu timeout"""
        try:
            result = subprocess.run(["bcdedit", "/timeout", str(seconds)],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            return result.returncode == 0
        except Exception as e:
            print(f"Error setting timeout: {e}")
            return False
    
    def get_timeout(self):
        """Get the current boot menu timeout"""
        try:
            result = subprocess.run(["bcdedit", "/enum", "{bootmgr}"],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode != 0:
                return 30
            timeout_key = self.get_translation("timeout").lower()
            pattern = rf'{timeout_key}\s+(\d+)'
            match = re.search(pattern, result.stdout, re.IGNORECASE)
            if match:
                return int(match.group(1))
            match = re.search(r'timeout\s+(\d+)', result.stdout, re.IGNORECASE)
            if match:
                return int(match.group(1))
            return 30
        except Exception as e:
            print(f"Error getting timeout: {e}")
            return 30
    
    def add_entry(self, description, device=None, path=None, type=None):
        """Add a new boot entry"""
        try:
            result = subprocess.run(["bcdedit", "/copy", "{current}", "/d", description],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            if result.returncode != 0:
                print(f"Error creating entry: {result.stderr}")
                return None
            match = re.search(r'({[a-fA-F0-9\-]+})', result.stdout)
            if not match:
                print("Could not find identifier of new entry")
                return None
            new_id = match.group(1)
            if device:
                device_result = subprocess.run(["bcdedit", "/set", new_id, "device", device],
                                               capture_output=True,
                                               text=True,
                                               errors="replace")
                if device_result.returncode != 0:
                    print(f"Warning: Failed to set device: {device_result.stderr}")
                subprocess.run(["bcdedit", "/set", new_id, "osdevice", device],
                               capture_output=True,
                               text=True,
                               errors="replace")
            if path:
                path_result = subprocess.run(["bcdedit", "/set", new_id, "path", path],
                                             capture_output=True,
                                             text=True,
                                             errors="replace")
                if path_result.returncode != 0:
                    print(f"Warning: Failed to set path: {path_result.stderr}")
            if type:
                type_result = subprocess.run(["bcdedit", "/set", new_id, "type", type],
                                             capture_output=True,
                                             text=True,
                                             errors="replace")
                if type_result.returncode != 0:
                    print(f"Warning: Failed to set type: {type_result.stderr}")
            return new_id
        except Exception as e:
            print(f"Error adding entry: {e}")
            return None
    
    def create_vhd_boot_entry(self, description, vhd_path):
        """Create a boot entry for a VHD/VHDX file"""
        try:
            new_id = self.add_entry(description)
            if not new_id:
                return None
            device_result = subprocess.run(["bcdedit", "/set", new_id, "device", f"vhd=[{vhd_path}]"],
                                           capture_output=True,
                                           text=True,
                                           errors="replace")
            osdevice_result = subprocess.run(["bcdedit", "/set", new_id, "osdevice", f"vhd=[{vhd_path}]"],
                                             capture_output=True,
                                             text=True,
                                             errors="replace")
            subprocess.run(["bcdedit", "/set", new_id, "detecthal", "yes"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            subprocess.run(["bcdedit", "/set", new_id, "nx", "OptIn"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            return new_id
        except Exception as e:
            print(f"Error creating VHD boot entry: {e}")
            return None
    
    def delete_entry(self, identifier):
        """Delete a boot entry"""
        try:
            result = subprocess.run(["bcdedit", "/delete", identifier],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            return result.returncode == 0
        except Exception as e:
            print(f"Error deleting entry: {e}")
            return False
    
    def modify_entry(self, identifier, option, value):
        """Modify a boot entry option"""
        try:
            result = subprocess.run(["bcdedit", "/set", identifier, option, value],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            return result.returncode == 0
        except Exception as e:
            print(f"Error modifying entry: {e}")
            return False
    
    def delete_entry_value(self, identifier, option):
        """Delete a value from a boot entry"""
        try:
            result = subprocess.run(["bcdedit", "/deletevalue", identifier, option],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            return result.returncode == 0
        except Exception as e:
            print(f"Error deleting entry value: {e}")
            return False
    
    def add_ramdisk(self, identifier, sdi_device, sdi_path, processor_arch="x64"):
        """Add ramdisk configuration to a boot entry"""
        try:
            device_result = subprocess.run(["bcdedit", "/set", identifier, "ramdisksdidevice", sdi_device],
                                           capture_output=True,
                                           text=True,
                                           errors="replace")
            path_result = subprocess.run(["bcdedit", "/set", identifier, "ramdisksdipath", sdi_path],
                                         capture_output=True,
                                         text=True,
                                         errors="replace")
            arch_result = subprocess.run(["bcdedit", "/set", identifier, "ramdisksdiprocessorarchitecture", processor_arch],
                                         capture_output=True,
                                         text=True,
                                         errors="replace")
            return (device_result.returncode == 0 and 
                    path_result.returncode == 0 and 
                    arch_result.returncode == 0)
        except Exception as e:
            print(f"Error adding ramdisk: {e}")
            return False
    
    def remove_ramdisk(self, identifier):
        """Remove ramdisk configuration from a boot entry"""
        try:
            subprocess.run(["bcdedit", "/deletevalue", identifier, "ramdisksdidevice"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            subprocess.run(["bcdedit", "/deletevalue", identifier, "ramdisksdipath"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            subprocess.run(["bcdedit", "/deletevalue", identifier, "ramdisksdiprocessorarchitecture"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            return True
        except Exception as e:
            print(f"Error removing ramdisk: {e}")
            return False
    
    def export_bcd(self, filename):
        """Export the BCD store to a file"""
        try:
            result = subprocess.run(["bcdedit", "/export", filename],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            return result.returncode == 0
        except Exception as e:
            print(f"Error exporting BCD: {e}")
            return False
    
    def import_bcd(self, filename):
        """Import the BCD store from a file"""
        try:
            result = subprocess.run(["bcdedit", "/import", filename],
                                    capture_output=True,
                                    text=True,
                                    errors="replace")
            return result.returncode == 0
        except Exception as e:
            print(f"Error importing BCD: {e}")
            return False
    
    def enable_kernel_debugging(self, identifier, port=None, baudrate=None):
        """Enable kernel debugging for a boot entry"""
        try:
            debug_result = subprocess.run(["bcdedit", "/set", identifier, "debug", "on"],
                                          capture_output=True,
                                          text=True,
                                          errors="replace")
            if port:
                port_result = subprocess.run(["bcdedit", "/set", identifier, "debugport", port],
                                             capture_output=True,
                                             text=True,
                                             errors="replace")
                if port_result.returncode != 0:
                    print(f"Warning: Failed to set debug port: {port_result.stderr}")
            if baudrate:
                baud_result = subprocess.run(["bcdedit", "/set", identifier, "debugbaudrate", baudrate],
                                             capture_output=True,
                                             text=True,
                                             errors="replace")
                if baud_result.returncode != 0:
                    print(f"Warning: Failed to set debug baudrate: {baud_result.stderr}")
            return debug_result.returncode == 0
        except Exception as e:
            print(f"Error enabling kernel debugging: {e}")
            return False
    
    def disable_kernel_debugging(self, identifier):
        """Disable kernel debugging for a boot entry"""
        try:
            debug_result = subprocess.run(["bcdedit", "/set", identifier, "debug", "off"],
                                          capture_output=True,
                                          text=True,
                                          errors="replace")
            subprocess.run(["bcdedit", "/deletevalue", identifier, "debugport"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            subprocess.run(["bcdedit", "/deletevalue", identifier, "debugbaudrate"],
                           capture_output=True,
                           text=True,
                           errors="replace")
            return debug_result.returncode == 0
        except Exception as e:
            print(f"Error disabling kernel debugging: {e}")
            return False

class BootManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Windows Boot Manager")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        try:
            self.root.iconbitmap(default="winapp")
        except:
            pass
        self.boot_manager = AdvancedBootManager()
        self.bg_thread_running = False
        self.create_ui()
        self.refresh_entries()
    
    def create_ui(self):
        """Create the user interface"""
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Refresh", command=self.refresh_entries)
        file_menu.add_separator()
        file_menu.add_command(label="Export BCD Store...", command=self.export_bcd)
        file_menu.add_command(label="Import BCD Store...", command=self.import_bcd)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        entry_menu = tk.Menu(self.menu_bar, tearoff=0)
        entry_menu.add_command(label="Add Boot Entry", command=self.add_entry)
        entry_menu.add_command(label="Add VHD Boot Entry", command=self.add_vhd_entry)
        entry_menu.add_separator()
        entry_menu.add_command(label="Delete Entry", command=self.delete_entry)
        entry_menu.add_command(label="Modify Entry", command=self.modify_entry)
        entry_menu.add_separator()
        entry_menu.add_command(label="Set as Default", command=self.set_default)
        entry_menu.add_separator()
        entry_menu.add_command(label="Move Up", command=self.move_entry_up)
        entry_menu.add_command(label="Move Down", command=self.move_entry_down)
        self.menu_bar.add_cascade(label="Entry", menu=entry_menu)
        
        options_menu = tk.Menu(self.menu_bar, tearoff=0)
        options_menu.add_command(label="Set Timeout", command=self.set_timeout_dialog)
        options_menu.add_separator()
        options_menu.add_command(label="Add Ramdisk Configuration", command=self.add_ramdisk)
        options_menu.add_command(label="Remove Ramdisk Configuration", command=self.remove_ramdisk)
        options_menu.add_separator()
        options_menu.add_command(label="Enable Kernel Debugging", command=self.enable_debugging)
        options_menu.add_command(label="Disable Kernel Debugging", command=self.disable_debugging)
        self.menu_bar.add_cascade(label="Options", menu=options_menu)
        
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(self.paned_window, width=300)
        self.paned_window.add(left_frame, weight=1)
        
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(list_container, text="Boot Entries:").pack(anchor=tk.W, pady=(0, 5))
        list_frame = ttk.Frame(list_container)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.entry_list = ttk.Treeview(list_frame, columns=("Description", "Type", "Status"), 
                                       show="headings", selectmode="browse")
        self.entry_list.heading("Description", text="Description")
        self.entry_list.heading("Type", text="Type")
        self.entry_list.heading("Status", text="Status")
        self.entry_list.column("Description", width=150, stretch=True)
        self.entry_list.column("Type", width=80, stretch=False)
        self.entry_list.column("Status", width=80, stretch=False)
        
        entry_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.entry_list.yview)
        self.entry_list.configure(yscrollcommand=entry_scrollbar.set)
        
        self.entry_list.grid(row=0, column=0, sticky="nsew")
        entry_scrollbar.grid(row=0, column=1, sticky="ns")
        
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        legend_frame = ttk.LabelFrame(left_frame, text="Legend")
        legend_frame.pack(fill=tk.X, pady=5)
        
        legend_items = ttk.Frame(legend_frame)
        legend_items.pack(fill=tk.X, padx=5, pady=5)
        
        default_frame = ttk.Frame(legend_items)
        default_frame.pack(fill=tk.X, pady=2)
        default_color = ttk.Label(default_frame, background="#e6f2ff", width=3)
        default_color.pack(side=tk.LEFT, padx=5)
        ttk.Label(default_frame, text="Default Boot Entry").pack(side=tk.LEFT, padx=5)
        
        missing_frame = ttk.Frame(legend_items)
        missing_frame.pack(fill=tk.X, pady=2)
        missing_color = ttk.Label(missing_frame, background="#ffcccc", width=3)
        missing_color.pack(side=tk.LEFT, padx=5)
        ttk.Label(missing_frame, text="Missing Path or Device").pack(side=tk.LEFT, padx=5)
        
        uefi_frame = ttk.Frame(legend_items)
        uefi_frame.pack(fill=tk.X, pady=2)
        uefi_color = ttk.Label(uefi_frame, background="#e6ffe6", width=3)
        uefi_color.pack(side=tk.LEFT, padx=5)
        ttk.Label(uefi_frame, text="UEFI Boot").pack(side=tk.LEFT, padx=5)
        
        bios_frame = ttk.Frame(legend_items)
        bios_frame.pack(fill=tk.X, pady=2)
        bios_color = ttk.Label(bios_frame, background="#fff2cc", width=3)
        bios_color.pack(side=tk.LEFT, padx=5)
        ttk.Label(bios_frame, text="Legacy/BIOS Boot").pack(side=tk.LEFT, padx=5)
        
        right_frame = ttk.Frame(self.paned_window, width=500)
        self.paned_window.add(right_frame, weight=2)
        
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        general_tab = ttk.Frame(self.notebook)
        self.notebook.add(general_tab, text="General")
        
        gen_frame = ttk.LabelFrame(general_tab, text="Entry Information")
        gen_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        row = 0
        ttk.Label(gen_frame, text="Identifier:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.id_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.id_var, state="readonly", width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1
        ttk.Label(gen_frame, text="Description:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.desc_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.desc_var, width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(gen_frame, text="Update", command=lambda: self.update_property("description")).grid(row=row, column=2, padx=5, pady=5)
        
        row += 1
        ttk.Label(gen_frame, text="Type:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.type_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.type_var, state="readonly", width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1
        ttk.Label(gen_frame, text="Device:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.device_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.device_var, width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(gen_frame, text="Update", command=lambda: self.update_property("device")).grid(row=row, column=2, padx=5, pady=5)
        
        row += 1
        ttk.Label(gen_frame, text="Path:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.path_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.path_var, width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Button(gen_frame, text="Update", command=lambda: self.update_property("path")).grid(row=row, column=2, padx=5, pady=5)
        
        row += 1
        ttk.Label(gen_frame, text="Default:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.default_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.default_var, state="readonly", width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1
        ttk.Label(gen_frame, text="Ramdisk:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.ramdisk_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.ramdisk_var, state="readonly", width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1
        ttk.Label(gen_frame, text="Boot Environment:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.bootenv_var = tk.StringVar()
        ttk.Entry(gen_frame, textvariable=self.bootenv_var, state="readonly", width=40).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        status_frame = ttk.Frame(gen_frame)
        status_frame.grid(row=row+1, column=0, columnspan=3, sticky="ew", padx=5, pady=10)
        
        action_frame = ttk.Frame(status_frame)
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="Set as Default", command=self.set_default).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Move Up", command=self.move_entry_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Move Down", command=self.move_entry_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Delete Entry", command=self.delete_entry).pack(side=tk.LEFT, padx=2)
        
        gen_frame.grid_columnconfigure(1, weight=1)
        
        raw_tab = ttk.Frame(self.notebook)
        self.notebook.add(raw_tab, text="Raw Details")
        
        self.details_text = scrolledtext.ScrolledText(raw_tab, wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        adv_tab = ttk.Frame(self.notebook)
        self.notebook.add(adv_tab, text="Advanced")
        
        adv_frame = ttk.Frame(adv_tab)
        adv_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ramdisk_frame = ttk.LabelFrame(adv_frame, text="Ramdisk Configuration")
        ramdisk_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ramdisk_buttons = ttk.Frame(ramdisk_frame)
        ramdisk_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(ramdisk_buttons, text="Add Ramdisk", command=self.add_ramdisk).pack(side=tk.LEFT, padx=5)
        ttk.Button(ramdisk_buttons, text="Remove Ramdisk", command=self.remove_ramdisk).pack(side=tk.LEFT, padx=5)
        
        debug_frame = ttk.LabelFrame(adv_frame, text="Kernel Debugging")
        debug_frame.pack(fill=tk.X, padx=5, pady=5)
        
        debug_buttons = ttk.Frame(debug_frame)
        debug_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(debug_buttons, text="Enable Debugging", command=self.enable_debugging).pack(side=tk.LEFT, padx=5)
        ttk.Button(debug_buttons, text="Disable Debugging", command=self.disable_debugging).pack(side=tk.LEFT, padx=5)
        
        boot_frame = ttk.LabelFrame(adv_frame, text="Boot Options")
        boot_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(boot_frame, text="Boot Timeout (seconds):").pack(side=tk.LEFT, padx=5, pady=5)
        
        self.timeout_var = tk.StringVar()
        timeout_entry = ttk.Entry(boot_frame, textvariable=self.timeout_var, width=5)
        timeout_entry.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(boot_frame, text="Set Timeout", command=self.set_timeout).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        ttk.Button(toolbar, text="Refresh", command=self.refresh_entries).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(toolbar, text="Add Entry", command=self.add_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Add VHD Entry", command=self.add_vhd_entry).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(toolbar, text="Export BCD", command=self.export_bcd).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Import BCD", command=self.import_bcd).pack(side=tk.LEFT, padx=2)
        
        self.entry_list.bind("<<TreeviewSelect>>", self.on_entry_select)
        
        self.entry_list.tag_configure("default", background="#e6f2ff")
        self.entry_list.tag_configure("missing", background="#ffcccc")
        self.entry_list.tag_configure("uefi", background="#e6ffe6")
        self.entry_list.tag_configure("legacy", background="#fff2cc")
    
    def refresh_entries(self):
        """Refresh the boot entries list"""
        for item in self.entry_list.get_children():
            self.entry_list.delete(item)
        identifiers = self.boot_manager.list_identifiers()
        if not identifiers:
            self.status_var.set("No boot entries found")
            return
        default_id = self.boot_manager.get_default_entry()
        for id in identifiers:
            if id.lower() == "{bootmgr}":
                continue
            description = self.boot_manager.get_entry_description(id)
            entry_type = self.boot_manager.get_entry_type(id)
            is_uefi = self.boot_manager.check_uefi(id)
            boot_env = "UEFI" if is_uefi else "Legacy"
            has_missing = self.boot_manager.has_missing_path_or_device(id)
            status_text = ""
            if has_missing:
                status_text = "Missing data"
            elif is_uefi:
                status_text = "UEFI"
            else:
                status_text = "Legacy"
            item = self.entry_list.insert("", tk.END, text=id, values=(description, entry_type, status_text))
            tags = []
            if id == default_id:
                tags.append("default")
            if has_missing:
                tags.append("missing")
            elif is_uefi:
                tags.append("uefi")
            else:
                tags.append("legacy")
            if tags:
                self.entry_list.item(item, tags=tags)
        timeout = self.boot_manager.get_timeout()
        self.timeout_var.set(str(timeout))
        self.status_var.set(f"Loaded {len(self.entry_list.get_children())} boot entries")
        if self.entry_list.get_children():
            self.entry_list.selection_set(self.entry_list.get_children()[0])
            self.on_entry_select(None)
    
    def on_entry_select(self, event):
        """Handle entry selection"""
        selection = self.entry_list.selection()
        if not selection:
            return
        item = selection[0]
        identifier = self.entry_list.item(item, "text")
        self.update_entry_details(identifier)
    
    def update_entry_details(self, identifier):
        """Update the details view for the selected entry"""
        details = self.boot_manager.get_entry_info(identifier)
        if not details:
            self.clear_details()
            return
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, details)
        self.id_var.set(identifier)
        self.desc_var.set(self.boot_manager.get_entry_description(identifier))
        self.type_var.set(self.boot_manager.get_entry_type(identifier))
        self.device_var.set(self.boot_manager.get_entry_device(identifier))
        self.path_var.set(self.boot_manager.get_entry_path(identifier))
        default_id = self.boot_manager.get_default_entry()
        if identifier == default_id:
            self.default_var.set("Yes")
        else:
            self.default_var.set("No")
        has_ramdisk = self.boot_manager.check_ramdisk(identifier)
        self.ramdisk_var.set("Yes" if has_ramdisk else "No")
        is_uefi = self.boot_manager.check_uefi(identifier)
        self.bootenv_var.set("UEFI" if is_uefi else "BIOS/Legacy")
    
    def clear_details(self):
        """Clear all entry details"""
        self.id_var.set("")
        self.desc_var.set("")
        self.type_var.set("")
        self.device_var.set("")
        self.path_var.set("")
        self.default_var.set("")
        self.ramdisk_var.set("")
        self.bootenv_var.set("")
        self.details_text.delete(1.0, tk.END)
    
    def get_selected_entry(self):
        """Get the identifier of the selected entry"""
        selection = self.entry_list.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a boot entry first")
            return None
        item = self.entry_list.selection()[0]
        return self.entry_list.item(item, "text")
    
    def update_property(self, property_name):
        """Update a property of the selected entry"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        value = ""
        if property_name == "description":
            value = self.desc_var.get()
        elif property_name == "device":
            value = self.device_var.get()
        elif property_name == "path":
            value = self.path_var.get()
        if not value:
            messagebox.showwarning("Empty Value", f"Please enter a value for {property_name}")
            return
        if self.boot_manager.modify_entry(identifier, property_name, value):
            self.status_var.set(f"Updated {property_name} for {identifier}")
            self.refresh_entries()
        else:
            self.status_var.set(f"Failed to update {property_name}")
    
    def add_entry(self):
        """Add a new boot entry"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Boot Entry")
        dialog.geometry("500x250")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Description:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        description_var = tk.StringVar()
        ttk.Entry(frame, textvariable=description_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(frame, text="Device (e.g., partition=C:):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        device_var = tk.StringVar()
        ttk.Entry(frame, textvariable=device_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(frame, text="Path (e.g., \\Windows\\system32\\winload.efi):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        path_var = tk.StringVar()
        ttk.Entry(frame, textvariable=path_var, width=40).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(frame, text="Type:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        type_var = tk.StringVar()
        type_combo = ttk.Combobox(frame, textvariable=type_var, width=40)
        types = self.boot_manager.get_entry_types()
        type_combo['values'] = types
        type_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        def on_ok():
            description = description_var.get()
            device = device_var.get()
            path = path_var.get()
            entry_type = type_var.get()
            if not description:
                messagebox.showerror("Input Error", "Description is required")
                return
            dialog.destroy()
            new_id = self.boot_manager.add_entry(description, device, path, entry_type)
            if new_id:
                self.refresh_entries()
                self.status_var.set(f"Added new boot entry: {description}")
                for item in self.entry_list.get_children():
                    if self.entry_list.item(item, "text") == new_id:
                        self.entry_list.selection_set(item)
                        self.on_entry_select(None)
                        break
            else:
                self.status_var.set("Failed to add boot entry")
        ttk.Button(button_frame, text="Add", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        frame.columnconfigure(1, weight=1)
    
    def add_vhd_entry(self):
        """Add a new VHD boot entry"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add VHD Boot Entry")
        dialog.geometry("500x200")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Description:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        description_var = tk.StringVar()
        ttk.Entry(frame, textvariable=description_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(frame, text="VHD/VHDX File:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        vhd_path_var = tk.StringVar()
        path_frame = ttk.Frame(frame)
        path_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Entry(path_frame, textvariable=vhd_path_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        def browse_vhd():
            filename = filedialog.askopenfilename(
                title="Select VHD/VHDX File",
                filetypes=[("VHD Files", "*.vhd"), ("VHDX Files", "*.vhdx"), ("All Files", "*.*")]
            )
            if filename:
                vhd_path_var.set(filename)
        ttk.Button(path_frame, text="Browse...", command=browse_vhd).pack(side=tk.RIGHT, padx=(5, 0))
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        def on_ok():
            description = description_var.get()
            vhd_path = vhd_path_var.get()
            if not description:
                messagebox.showerror("Input Error", "Description is required")
                return
            if not vhd_path:
                messagebox.showerror("Input Error", "VHD/VHDX file path is required")
                return
            dialog.destroy()
            new_id = self.boot_manager.create_vhd_boot_entry(description, vhd_path)
            if new_id:
                self.refresh_entries()
                self.status_var.set(f"Added new VHD boot entry: {description}")
                for item in self.entry_list.get_children():
                    if self.entry_list.item(item, "text") == new_id:
                        self.entry_list.selection_set(item)
                        self.on_entry_select(None)
                        break
            else:
                self.status_var.set("Failed to add VHD boot entry")
        ttk.Button(button_frame, text="Add", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        frame.columnconfigure(1, weight=1)
    
    def delete_entry(self):
        """Delete the selected boot entry"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        if not messagebox.askyesno("Confirm Delete", 
                                   f"Are you sure you want to delete the boot entry '{identifier}'?\n\n"
                                   "This action cannot be undone."):
            return
        if self.boot_manager.delete_entry(identifier):
            self.refresh_entries()
            self.status_var.set(f"Deleted boot entry: {identifier}")
        else:
            self.status_var.set(f"Failed to delete boot entry: {identifier}")
    
    def modify_entry(self):
        """Modify the selected boot entry with custom options"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Modify Boot Entry")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        entry_info = self.boot_manager.get_entry_info(identifier)
        if not entry_info:
            dialog.destroy()
            self.status_var.set(f"Failed to get entry information: {identifier}")
            return
        ttk.Label(frame, text="Entry ID:").pack(anchor=tk.W)
        id_var = tk.StringVar(value=identifier)
        ttk.Entry(frame, textvariable=id_var, state="readonly").pack(fill=tk.X, pady=(0, 10))
        ttk.Label(frame, text="Enter option and value to modify:").pack(anchor=tk.W)
        option_frame = ttk.Frame(frame)
        option_frame.pack(fill=tk.X, pady=5)
        ttk.Label(option_frame, text="Option:").pack(side=tk.LEFT)
        option_var = tk.StringVar()
        option_combo = ttk.Combobox(option_frame, textvariable=option_var, width=30)
        option_combo['values'] = ('description', 'device', 'path', 'osdevice', 'timeout', 'nx', 'bootmenupolicy', 
                                   'detecthal', 'winpe', 'nointegritychecks', 'testsigning')
        option_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        value_frame = ttk.Frame(frame)
        value_frame.pack(fill=tk.X, pady=5)
        ttk.Label(value_frame, text="Value:").pack(side=tk.LEFT)
        value_var = tk.StringVar()
        ttk.Entry(value_frame, textvariable=value_var, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(frame, text="Current Settings:").pack(anchor=tk.W, pady=(10, 0))
        settings_text = scrolledtext.ScrolledText(frame, height=8, wrap=tk.WORD)
        settings_text.pack(fill=tk.BOTH, expand=True, pady=5)
        settings_text.insert(tk.END, entry_info)
        settings_text.configure(state="disabled")
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        def on_apply():
            option = option_var.get()
            value = value_var.get()
            if not option:
                messagebox.showerror("Input Error", "Option is required")
                return
            if self.boot_manager.modify_entry(identifier, option, value):
                self.refresh_entries()
                self.update_entry_details(identifier)
                self.status_var.set(f"Modified {option} for {identifier}")
                settings_text.configure(state="normal")
                settings_text.delete(1.0, tk.END)
                new_info = self.boot_manager.get_entry_info(identifier)
                settings_text.insert(tk.END, new_info)
                settings_text.configure(state="disabled")
                option_var.set("")
                value_var.set("")
            else:
                self.status_var.set(f"Failed to modify {option}")
        ttk.Button(button_frame, text="Apply", command=on_apply).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def set_default(self):
        """Set the selected entry as the default boot entry"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        if self.boot_manager.set_default_entry(identifier):
            self.refresh_entries()
            self.status_var.set(f"Set {identifier} as default boot entry")
        else:
            self.status_var.set(f"Failed to set default boot entry: {identifier}")
    
    def move_entry_up(self):
        """Move the selected entry up in the boot order"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        if self.boot_manager.move_entry_up(identifier):
            self.refresh_entries()
            self.status_var.set(f"Moved {identifier} up in boot order")
        else:
            self.status_var.set(f"Failed to move entry up: {identifier}")
    
    def move_entry_down(self):
        """Move the selected entry down in the boot order"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        if self.boot_manager.move_entry_down(identifier):
            self.refresh_entries()
            self.status_var.set(f"Moved {identifier} down in boot order")
        else:
            self.status_var.set(f"Failed to move entry down: {identifier}")
    
    def set_timeout(self):
        """Set the boot menu timeout"""
        try:
            timeout = int(self.timeout_var.get())
            if timeout < 0:
                messagebox.showerror("Input Error", "Timeout must be a positive integer")
                return
            if self.boot_manager.set_timeout(timeout):
                self.status_var.set(f"Set boot menu timeout to {timeout} seconds")
            else:
                self.status_var.set("Failed to set boot menu timeout")
        except ValueError:
            messagebox.showerror("Input Error", "Timeout must be a valid integer")
    
    def set_timeout_dialog(self):
        """Show a dialog to set the boot menu timeout"""
        current_timeout = self.boot_manager.get_timeout()
        new_timeout = simpledialog.askinteger(
            "Boot Timeout", 
            "Enter the boot menu timeout in seconds:",
            initialvalue=current_timeout,
            minvalue=0,
            parent=self.root
        )
        if new_timeout is not None:
            if self.boot_manager.set_timeout(new_timeout):
                self.timeout_var.set(str(new_timeout))
                self.status_var.set(f"Set boot menu timeout to {new_timeout} seconds")
            else:
                self.status_var.set("Failed to set boot menu timeout")
    
    def add_ramdisk(self):
        """Add ramdisk configuration to the selected entry"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Ramdisk Configuration")
        dialog.geometry("500x200")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="SDI Device (e.g., partition=C:):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        device_var = tk.StringVar()
        ttk.Entry(frame, textvariable=device_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(frame, text="SDI Path (e.g., \\boot\\boot.sdi):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        path_var = tk.StringVar()
        path_frame = ttk.Frame(frame)
        path_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Entry(path_frame, textvariable=path_var, width=30).pack(side=tk.LEFT, fill=tk.X, expand=True)
        def browse_sdi():
            filename = filedialog.askopenfilename(
                title="Select SDI File",
                filetypes=[("SDI Files", "*.sdi"), ("All Files", "*.*")]
            )
            if filename:
                path_var.set(filename)
        ttk.Button(path_frame, text="Browse...", command=browse_sdi).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Label(frame, text="Processor Architecture:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        arch_var = tk.StringVar(value="x64")
        arch_combo = ttk.Combobox(frame, textvariable=arch_var, width=30)
        arch_combo['values'] = ('x86', 'x64', 'arm')
        arch_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        def on_ok():
            device = device_var.get()
            path = path_var.get()
            arch = arch_var.get()
            if not device or not path:
                messagebox.showerror("Input Error", "Both device and path are required")
                return
            dialog.destroy()
            if self.boot_manager.add_ramdisk(identifier, device, path, arch):
                self.refresh_entries()
                self.update_entry_details(identifier)
                self.status_var.set(f"Added ramdisk configuration to {identifier}")
            else:
                self.status_var.set("Failed to add ramdisk configuration")
        ttk.Button(button_frame, text="Add", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        frame.columnconfigure(1, weight=1)
    
    def remove_ramdisk(self):
        """Remove ramdisk configuration from the selected entry"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        if not self.boot_manager.check_ramdisk(identifier):
            messagebox.showinfo("No Ramdisk", "The selected entry does not have ramdisk configuration")
            return
        if not messagebox.askyesno("Confirm Remove", 
                                   f"Are you sure you want to remove the ramdisk configuration from '{identifier}'?"):
            return
        if self.boot_manager.remove_ramdisk(identifier):
            self.refresh_entries()
            self.update_entry_details(identifier)
            self.status_var.set(f"Removed ramdisk configuration from {identifier}")
        else:
            self.status_var.set("Failed to remove ramdisk configuration")
    
    def enable_debugging(self):
        """Enable kernel debugging for the selected entry"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Enable Kernel Debugging")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Debug Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        port_var = tk.StringVar(value="1")
        port_combo = ttk.Combobox(frame, textvariable=port_var, width=30)
        port_combo['values'] = ('1', '2', '3', '4', 'usb')
        port_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Label(frame, text="Baud Rate:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(frame, textvariable=baud_var, width=30)
        baud_combo['values'] = ('9600', '19200', '38400', '57600', '115200')
        baud_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        def on_ok():
            port = port_var.get()
            baud = baud_var.get()
            dialog.destroy()
            if self.boot_manager.enable_kernel_debugging(identifier, port, baud):
                self.refresh_entries()
                self.update_entry_details(identifier)
                self.status_var.set(f"Enabled kernel debugging for {identifier}")
            else:
                self.status_var.set("Failed to enable kernel debugging")
        ttk.Button(button_frame, text="Enable", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        frame.columnconfigure(1, weight=1)
    
    def disable_debugging(self):
        """Disable kernel debugging for the selected entry"""
        identifier = self.get_selected_entry()
        if not identifier:
            return
        if not messagebox.askyesno("Confirm Disable", 
                                   f"Are you sure you want to disable kernel debugging for '{identifier}'?"):
            return
        if self.boot_manager.disable_kernel_debugging(identifier):
            self.refresh_entries()
            self.update_entry_details(identifier)
            self.status_var.set(f"Disabled kernel debugging for {identifier}")
        else:
            self.status_var.set("Failed to disable kernel debugging")
    
    def export_bcd(self):
        """Export the BCD store to a file"""
        filename = filedialog.asksaveasfilename(
            title="Export BCD Store",
            filetypes=[("BCD Files", "*.bcd"), ("All Files", "*.*")],
            defaultextension=".bcd"
        )
        if not filename:
            return
        if self.boot_manager.export_bcd(filename):
            self.status_var.set(f"Exported BCD store to {filename}")
        else:
            self.status_var.set("Failed to export BCD store")
    
    def import_bcd(self):
        """Import the BCD store from a file"""
        filename = filedialog.askopenfilename(
            title="Import BCD Store",
            filetypes=[("BCD Files", "*.bcd"), ("All Files", "*.*")]
        )
        if not filename:
            return
        if not messagebox.askyesno("Confirm Import", 
                                   f"Are you sure you want to import BCD store from {filename}?\n\n"
                                   "This will replace your current boot configuration."):
            return
        if self.boot_manager.import_bcd(filename):
            self.refresh_entries()
            self.status_var.set(f"Imported BCD store from {filename}")
        else:
            self.status_var.set("Failed to import BCD store")
    
    def show_about(self):
        """Show the about dialog"""
        about_dialog = tk.Toplevel(self.root)
        about_dialog.title("About Advanced Windows Boot Manager")
        about_dialog.geometry("400x300")
        about_dialog.transient(self.root)
        about_dialog.grab_set()
        frame = ttk.Frame(about_dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        title_font = Font(size=14, weight="bold")
        ttk.Label(frame, text="Advanced Windows Boot Manager", font=title_font).pack(pady=10)
        ttk.Label(frame, text="Version 1.1").pack()
        description = (
            "A comprehensive tool for managing Windows boot entries, "
            "including advanced options such as ramdisk configuration, "
            "VHD boot entries, and kernel debugging.\n\n"
            "Features multi-language support and enhanced visual indicators."
        )
        desc_label = ttk.Label(frame, text=description, wraplength=350, justify=tk.CENTER)
        desc_label.pack(pady=10)
        ttk.Label(frame, text=f"© {datetime.datetime.now().year}").pack(pady=5)
        ttk.Button(frame, text="Close", command=about_dialog.destroy).pack(pady=10)

def main():
    if not AdvancedBootManager().is_admin():
        messagebox.showerror("Administrator Required", 
                             "This application requires administrator privileges.\n"
                             "Please run this program as administrator.")
        return
    root = tk.Tk()
    app = BootManagerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
