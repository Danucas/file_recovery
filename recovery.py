#!/usr/bin/env python3

import re # used for regex queries
import struct # used to convert hex bytes to long integer
import binascii # used to convert hex strings to bytes
import argparse # parses command line arguments
import hashlib # used to calculate hashes
import sys # used to exit upon error
import shutil
import time
import PyPDF2
import json
import os
import docx

DEFAULT_MAX_FILE_SIZE = 10485760 # 10MB


signatures = [
              ['.mpg',  b'\x00\x00\x01\xB3.\x00', b'\x00\x00\x00\x01\xB7'],
              ['.mpg',  b'\x00\x00\x01\xBA.\x00', b'\x00\x00\x00\x01\xB9'],
              ['.pdf',  b'\x25\x50\x44\x46', b'\x25\x25\x45\x4F\x46'],
              # ['.bmp', b'\x42\x4D....\x00\x00\x00\x00', None],
              ['.gif', b'\x47\x49\x46\x38\x37\x61', b'\x00\x00\x3B'],
              ['.gif', b'\x47\x49\x46\x38\x39\x61', b'\x00\x00\x3B'],
              ['.jpg', b'\xFF\xD8\xFF\xE0', b'\xFF\xD9'],
              ['.jpg', b'\xFF\xD8\xFF\xE1', b'\xFF\xD9'],
              ['.jpg', b'\xFF\xD8\xFF\xE2', b'\xFF\xD9'],
              ['.jpg', b'\xFF\xD8\xFF\xE8', b'\xFF\xD9'],
              ['.jpg', b'\xFF\xD8\xFF\xDB', b'\xFF\xD9'],
              ['.docx', b'\x50\x4B\x03\x04\x14\x00\x06\x00', b'\x50\x4B\x05\x06'],
              # ['.avi', b'\x52\x49\x46\x46....\x41\x56\x49\x20\x4C\x49\x53\x54', None],
              ['.png', b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A', b'\x49\x45\x4E\x44\xAE\x42\x60\x82']
]# 80309168

# 64 kb chunk size
BUF_SIZE = 512
DISK = 'D'
disk_path = f'\\\\.\\{DISK}:'


found_files = {}


def save_status(data):
    status = get_status()
    status.update(data)

    with open('status.json', 'w+') as status_file:
        status_file.write(json.dumps(status))


def get_status():
    if os.path.exists('status.json'):
        with open('status.json', 'r') as status_file:
            return json.loads(status_file.read())
    else:
        return {}


def get_percent(address, total):
    percent = address * 100 / total
    return round(percent, 2)


def read_temp_scan(disk):
    try:
        with open(f'{disk}_recovery.json', 'r') as temp_file:
            file_formats_dict = json.loads(temp_file.read())
            # Remove Duplicates for each file_format
            file_formats_dict = {key: list(set(values)) for key, values in file_formats_dict.items()}
            return file_formats_dict
    except:
        return {}

def save_temp_scan(disk, data):
    # Remove Duplicates for each file_format
    data = {key: list(set(values)) for key, values in data.items()}
    with open(f'{disk}_recovery.json', 'w+') as temp_file:
        temp_file.write(json.dumps(data))


def recover_all(file_format, addresses, disk):
    init_time = time.time()
    save_status({'recovering': True})
    print(f'Recovering all {file_format} files in {disk}')

    errors = []

    for i, address in enumerate(addresses):
        msg = f'{time.time() - init_time} seconds'
        print(f'\r{disk}:\\.*{address}{file_format} {msg}', end='')

        perc = f'[ {round(i * 100 / len(addresses), 2)}% ]'
        remain = f'({i + 1}/{len(addresses)})'

        if file_exists_and_good(file_format, address, disk):
            save_status({'message': f'Skipping {address}{file_format}', 'progress': f'{perc} {remain}'})
            continue
        save_status({'message': msg, 'progress': f'{perc} {remain}'})

        state = get_status()
        if not state.get('recovering'):
            break

        try:
            recover_file(file_format, address, disk)
        except Exception as e:
            errors.append(e)
            print(e)

    save_status({'recovering': False, 'message': f'Recovering finished with {len(errors)} errors.'})

    print(f'\nRecovery Finished in {int(time.time() - init_time)}')


def check_eof(file_format, data, offset):
    for signature in signatures:
        extension, sign, eof = signature
        if extension != file_format:
            continue
        found = data.find(eof)

        if found >= 1:
            return offset + found, len(eof)
    return None, 0


def get_file_eof(file_format, address, disk):

    signs = [signature[1] for signature in signatures if signature[0] == file_format]
    start_time = time.time()
    BUFFER_SIZE = 512

    if file_format == '.mpg':
        BUFFER_SIZE = DEFAULT_MAX_FILE_SIZE * 10

    exact_pointer = 512 * int(address / 512)
    disk_path = f'\\\\.\\{disk}:'

    size = 0

    with open(disk_path, 'rb') as drive:
        # Go to the file signature
        drive.seek(exact_pointer)
        buffer_data = drive.read(BUFFER_SIZE)
        size += len(buffer_data)

        itera = 0
        while buffer_data:
            if size > DEFAULT_MAX_FILE_SIZE:
                return None, 0

            msg = f'[{address}{file_format}]: calculated size <{round(size * 0.000001, 2)} MB> -> elapsed time: {round(time.time() - start_time, 2)}'
            print(f'\r{msg}', end='')
            save_status({'message': msg})
            eof, eof_length = check_eof(file_format, buffer_data, exact_pointer)
            if eof:
                print(f'Finished in {time.time() - start_time}')
                print(f'Calculated size: {eof - address} {(eof - address) * 0.000001} MB')

                return eof, eof_length
            
            # Check if another file beings
            if itera > 0:
                for sign in signs:
                    found = buffer_data.find(sign)
                    if found >= 1:
                        return exact_pointer + found, 0

            exact_pointer = drive.tell()
            buffer_data = drive.read(BUFFER_SIZE)
            if buffer_data:
                size += len(buffer_data)
            itera += 1
        print()
    return None, 0


def write_batch(file_path, data):
    with open(file_path, 'ab') as batched_file:
        batched_file.write(data)


def generate_recovery_file(file_format, pointer, disk):
    file_path = f"recovered/{disk}"

    if not os.path.exists(file_path):
        os.mkdir(file_path)
    
    file_path = f"{file_path}/{file_format.replace('.', '')}"

    if not os.path.exists(file_path):
        os.mkdir(file_path)
    
    file_path = f'{file_path}/{pointer}{file_format}'
    
    with open(file_path, 'wb') as recovered_file:
        recovered_file.write(b'')
    
    return file_path


def update_eof_registry(file_format, pointer, disk):
    pass


def recover_single_file(file_format, pointer, disk):
    save_status({'recovering': True})
    recover_file(file_format, pointer, disk)
    save_status({'recovering': False})


def recover_file(file_format, pointer, disk):
    exact_pointer = 512 * int(pointer / 512)
    disk_path = f'\\\\.\\{disk}:'
    BUF_SIZE = 1024
    start_time = time.time()

    total, used, free = shutil.disk_usage(f'{disk_path}\\')
    print(f'Getting EOF for {pointer}{file_format}')

    eof, eof_length = get_file_eof(file_format, pointer, disk)

    if not eof:
        print('EOF not found quit.')
        return
    
    print(f'EOF found at {eof}')

    output_file = generate_recovery_file(file_format, pointer, disk)

    print(f'Output File: {output_file}')

    # Set the Buffer size for mpg and large file_formats
    calculated_size = eof - pointer

    if file_format == '.mpg':
        BUF_SIZE = DEFAULT_MAX_FILE_SIZE
    if calculated_size > DEFAULT_MAX_FILE_SIZE:
        BUF_SIZE = DEFAULT_MAX_FILE_SIZE


    # Open the disk
    iteration = 0
    with open(disk_path, 'rb') as drive:
        # Move to the beginning or the more accurate location
        try:
            drive.seek(exact_pointer, 0)
        except Exception as e:
            print(e)
            return
        # Read the first chunk
        bytes_data = drive.read(BUF_SIZE)

        # Use stop signal
        stop = False
        while bytes_data and not stop:
            msg = f'[{pointer}{file_format}]({calculated_size}) -> {(drive.tell() - pointer) * 100 / calculated_size}'
            print(f'\r{msg}', end='')
            if iteration == 0:
                bytes_data = bytes_data[pointer - exact_pointer:]

            if drive.tell() > eof:
                pos = drive.tell() - eof
                bytes_data = bytes_data[:-(pos) + eof_length]
                try:
                    write_batch(output_file, bytes_data)
                except Exception as e:
                    print('\nError recovering file\nBytes Data:')
                    print(pos, drive.tell(), eof, eof_length, len(bytes_data))
                    return
                stop = True

            
            if not stop:
                write_batch(output_file, bytes_data)

            bytes_data = drive.read(BUF_SIZE)
            iteration += 1
    
    check_file(file_format, output_file, disk)
    print(f'\n File Recovery Succeed found the file at {os.getcwd()}{output_file}')


def check_file(file_format, output_file, disk):
    file_format = file_format.replace('.', '')
    if file_format == 'pdf':
        try:
            with open(output_file, 'rb') as file_obj:
                print(f'Reading {file_format}')
                reader = PyPDF2.PdfReader(file_obj)
                print(len(reader.pages))
                return True

        except Exception as e:
            print('PDF Exception', e)
            try:
                delete_file(output_file)
            except Exception as a:
                print('Delete file Exception', a)
            return False
    else:
        return True

def file_exists_and_good(file_format, pointer, disk):
    file_path = f'recovered/{disk}/{file_format.replace(".", "")}/{pointer}{file_format}'

    if os.path.exists(file_path):
        if check_file(file_format, file_path, disk):
            return True


def delete_file(file_path):
    os.remove(file_path)



def save_progress(elapsed, percent):
    save_status({
        'elapsed': elapsed,
        'percent': percent
    })


def fast_scan(disk, pointer=None):
    disk_path = f'\\\\.\\{disk}:'
    BUF_SIZE = DEFAULT_MAX_FILE_SIZE # Equals 60 MB
    total, used, free = shutil.disk_usage(f'{disk_path}\\')
    print(f'Scanning Disk: {disk_path}\nTotal Size in bytes: {total}')
    print(f'Last Checkpoint for this drive: {pointer} {hex(pointer)}')
    start_time = time.time()

    temp_matches = read_temp_scan(disk)

    with open(disk_path, 'rb') as drive:
        if pointer:
            # Move to this position
            fixed_position = BUF_SIZE * int(pointer / BUF_SIZE)
            print(f'Move pointer to offset fixed position {fixed_position}')
            drive.seek(fixed_position, 0)

        bytes_data = drive.read(BUF_SIZE)
        offs = 0 if not pointer else int(pointer / BUF_SIZE)
        calculate_total = lambda x: sum([len(addresses) for addresses in x.values()])
        
        while bytes_data:
            state = get_status()
            if not state.get('running'):
                print('\nStopping Scanner')
                return
            # total_found = calculate_total(temp_matches)
            elapsed = time.time() - start_time
            percent = get_percent(drive.tell(), total)

            print(f'\rProgress: {percent}%  time: {int(elapsed)} seconds  ', end='')
            save_progress(elapsed, percent)

            for signature in signatures:
                extension, sign, eof = signature
                matches = [f.start() + (BUF_SIZE * offs) for f in re.finditer(sign, bytes_data)]
                if temp_matches.get(extension):
                    temp_matches[extension].extend(matches)
                else:
                    temp_matches[extension] = [*matches]
        
            bytes_data = drive.read(BUF_SIZE)
            offs +=1
            save_temp_scan(disk, temp_matches)

    save_status({'running': False})
    
    print(f'\nScanning finished in {int(time.time() - start_time)} seconds')



def fix_corrupted_file(file_format, file_path):
    with open(file_path, 'rb') as file_to_fix:
        file_to_fix.seek(24)