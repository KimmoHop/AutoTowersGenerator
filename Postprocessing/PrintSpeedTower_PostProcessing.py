# This script modifies the printing speed for a print speed tower
#
# Cura does not use a single "print speed" when slicing a model, but uses
# different values for infill, inner walls, outer walls, etc.
# This script modifies each section of the speed tower while maintaining the
# different speeds, so it should accurately represent how Cura would slice
# for each speed.
#
# Version 1.0 - 29 Sep 2022:
#   Split off from MiscSpeedTower_PostProcessing to focus exclusively on print speed towers
# Version 1.1 - 05 Nov 2022:
#   Renamed from TravelSpeedTower_PostProcessing.py to PrintSpeedTower_PostProcessing.py 
#       to better match what it actually does
# Version 1.2 - 05 Nov 2022:
#   Fixed an issue with recognizing decimal speeds in gcode
#   Now only displaying LCD messages for the nominal speed for each layer
# Version 1.3 - 25 Nov 2022:
#   Updated to ignore user-specified "End G-Code"
#   Rearchitected how lines are processed
# Version 1.4 - 26 Nov 2022:
#   Moved common code to PostProcessingCommon.py
# Version 2.0 - 1 Dec 2022:
#   Redesigned post-processing to focus on section *height* rather than section *layers*
#   This is more accurate if the section height cannot be evenly divided by the printing layer height
__version__ = '2.0'

from UM.Logger import Logger

import re

from . import PostProcessingCommon as Common



def execute(gcode, base_height:float, section_height:float, initial_layer_height:float, layer_height:float, start_speed:float, speed_change:float, reference_speed:float, enable_lcd_messages:bool):
    ''' Post-process gcode sliced by Cura
        Note that reference_speed is the print speed selection when the gcode was generated 
            This value is used to determine how print speed settings in the
            gcode are modified for each level '''
    
    # Log the post-processing settings
    Logger.log('d', 'AutoTowersGenerator beginning print speed SpeedTower post-processing')
    Logger.log('d', f'Base height = {base_height} mm')
    Logger.log('d', f'Section height = {section_height} mm')
    Logger.log('d', f'Initial printed layer height = {initial_layer_height}')
    Logger.log('d', f'Printed layer height = {layer_height} mm')
    Logger.log('d', f'Starting speed = {start_speed} mm/s')
    Logger.log('d', f'Speed change = {speed_change} mm/s')
    Logger.log('d', f'Reference speed = {reference_speed} mm/s')
    Logger.log('d', f'Enable LCD messages = {enable_lcd_messages}')

    # Document the settings in the g-code
    gcode[0] += f'{Common.comment_prefix} Post-processing a print speed SpeedTower\n'
    gcode[0] += f'{Common.comment_prefix} Base height = {base_height} mm\n'
    gcode[0] += f'{Common.comment_prefix} Section height = {section_height} mm\n'
    gcode[0] += f'{Common.comment_prefix} Initial printed layer height = {initial_layer_height} mm\n'
    gcode[0] += f'{Common.comment_prefix} Printed layer height = {layer_height} mm\n'
    gcode[0] += f'{Common.comment_prefix} Starting speed = {start_speed} mm/s\n'
    gcode[0] += f'{Common.comment_prefix} Speed change = {speed_change} mm/s\n'
    gcode[0] += f'{Common.comment_prefix} Reference speed = {reference_speed} mm/s\n'
    gcode[0] += f'{Common.comment_prefix} Enable LCD messages = {enable_lcd_messages}\n'

    # Start at the requested print speed
    current_speed = start_speed - speed_change # The current speed will be corrected when the first section is encountered

    # Iterate over each line in the g-code
    for line_index, line, lines, start_of_new_section in Common.LayerEnumerate(gcode, base_height, section_height, initial_layer_height, layer_height):

        # Handle each new section
        if start_of_new_section:

            # Increment the speed for the new tower section
            current_speed += speed_change

            # Document the new speed in the gcode
            lines.insert(2, f'{Common.comment_prefix} Print speed for this tower section is {current_speed:.1f} mm/s ({current_speed*60:.1f} mm/min)')

            # Display the new print speed on the printer's LCD
            if enable_lcd_messages:
                lines.insert(3, f'M117 SPD {current_speed:.1f} mm/s {Common.comment_prefix} Displaying "SPD {current_speed:.1f} mm/s" on the LCD')
        
        # Modify lines specifying print speed
        if Common.IsPrintSpeedLine(line):

            # Determine the old speed setting in the gcode
            oldSpeedResult = re.search(r'F(\d+(?:\.\d*)?)', line.split(';')[0])
            if oldSpeedResult:
                oldSpeedString = oldSpeedResult.group(1)
                oldSpeed = float(oldSpeedString)

                # Determine the new speed to set (converting mm/s to mm/m)
                # This is done based on the reference speed, or the
                # "print speed" value when the gcode was generated
                # Note that Cura specifies print speed as mm/s, but gcode needs it as mm/min
                newSpeed = (current_speed * 60) * oldSpeed / (reference_speed * 60)

                # Change the speed in the gcode
                lines[line_index] = line.replace(f'F{oldSpeedString}', f'F{newSpeed:.1f}') + f' {Common.comment_prefix} changing speed from {(oldSpeed/60):.1f} mm/s ({oldSpeed:.1f} mm/min) to {(newSpeed/60):.1f} mm/s ({newSpeed:.1f} mm/min)'
    
    Logger.log('d', f'AutoTowersGenerator completing SpeedTower post-processing (Print Speed)')

    return gcode
