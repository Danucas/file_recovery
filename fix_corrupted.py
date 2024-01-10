import PyPDF2
import os
from recovery import signatures
from gpt_repair import repair_pdf


valid_files = []

pdfs = [dire for dire in os.listdir('recovered/J/pdf') if '.pdf' in dire]

for file in pdfs:
    try:
        with open(f'recovered/J/pdf/{file}', 'rb') as file_obj:
            print(f'Reading {file}')

            reader = PyPDF2.PdfReader(file_obj)
            
            print(len(reader.pages))
            valid_files.append(file)

    except Exception as e:
        print(e)


print('Valid Files:', f'{len(valid_files)}/{len(pdfs)}', valid_files)

invalid_files = []


for file in pdfs:
    if file not in valid_files:
        invalid_files.append(file)
        print('Invalid File:', file)


for invalid in invalid_files:
    input_file = f'recovered/J/pdf/{invalid}'
    out_file = f'recovered/J/pdf/repaired/{invalid}'
    repair_pdf(input_file, out_file)
    # BUFFER_SIZE = 512
    # complete_buffer = None

    # print('Recovering', invalid)
    # with open(f'recovered/J/pdf/{invalid}', 'rb') as file_obj:
    #     file_obj.seek(8, 0)
    #     buffer = file_obj.read(BUFFER_SIZE)

    #     pos = 8
    #     file_eof = None

    #     while buffer:
    #         found = buffer.find(b'\x25\x25\x45\x4f\x46')
    #         if found >= 1:
    #             file_eof = pos + found + 5 # <- EOF length

    #         pos = file_obj.tell()
    #         buffer = file_obj.read(BUFFER_SIZE)
    #     file_obj.seek(0, 0)
    #     complete_buffer = file_obj.read(file_eof)
    
    # if complete_buffer:
    #     with open(f'recovered/J/pdf/recovered-{invalid}', 'wb+') as new_file:
    #         new_file.write(complete_buffer)

            

