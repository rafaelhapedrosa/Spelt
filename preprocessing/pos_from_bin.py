def pos_from_bin(path):
    '''
    Function for generating an Axona .pos position tracking file directly from raw recording data
    Input required is the path to the .set and .bin file (including the trial name, without the file extension, both files must be in the same directory)
    The .pos file will be written into this directory, and should be the same format as those generated by DacqUSB
    Jake Swann, 2023
    '''
    import pandas as pd
    
    header = []
    with open(f'{path}.set', 'r') as f:
        set_file = f.readlines()

    trial_duration = round(float(set_file[4][9:])) #Default Axona conversion rounds to a whole number of seconds
    header =  [set_file[0][:-1]+'\r\n',
               set_file[1][:-1]+'\r\n',
               set_file[2][:-1]+'\r\n',
               set_file[3][:-1]+'\r\n',
               set_file[4][:9] + str(trial_duration) + '       \r\n',
               set_file[5][:-1]+'\r\n',
               'num_colours 4\r\n',
               'min_x 0\r\n',
               'max_x 768\r\n',
               'min_y 0\r\n',
               'max_y 574\r\n',
               'window_min_x ' + str(set_file[1059][5:-1])+'\r\n',
               'window_max_x ' + str(set_file[1060][5:-1])+'\r\n',
               'window_min_y ' + str(set_file[1061][5:-1])+'\r\n',
               'window_max_y ' + str(set_file[1062][5:-1])+'\r\n',
               'timebase 50 hz\r\n',
               'bytes_per_timestamp 4\r\n',
               'sample_rate 50.0 hz\r\n',
               'EEG_samples_per_position 5\r\n',
               'bearing_colour_1 ' + str(set_file[1420][15:-1]) +'\r\n',
               'bearing_colour_2 ' + str(set_file[1421][15:-1]) +'\r\n',
               'bearing_colour_3 ' + str(set_file[1422][15:-1]) +'\r\n',
               'bearing_colour_4 ' + str(set_file[1423][15:-1]) +'\r\n',
               'pos_format t,x1,y1,x2,y2,numpix1,numpix2\r\n',
               'bytes_per_coord 2\r\n',
               'pixels_per_metre ' + str(set_file[1099][25:-1])+'\r\n',
               'num_pos_samples ' + str(trial_duration*50) + '     \r\n', #Camera sample rate hard coded as 50 Hz
               'data_start'
                ]

    # read in data and extract position data
    with open(f'{path}.bin', 'rb') as f:
        data = f.read()

    position_data = []
    packetnums = []
    timestamps = []
    x1s = []
    y1s = []
    x2s = []
    y2s = []
    numpix1s = []
    numpix2s = []
    totalpixs = []

    for i in range(432, len(data)-432, 432): #skip first packet because it can be bugged (says Jim)
        packet = data[i:i+432]
        packet_id = packet[0:4].decode('ascii')

        if packet_id == 'ADU2':
            pos_sample = packet[12:32]

            #Flip digits in pos data for saving (this is how they are in the .pos relative to the .bin)
            pos_first = pos_sample[::2]
            pos_second = pos_sample[1::2]
            pos_sample = []
            for n, i in enumerate(pos_first):
                pos_sample.append(pos_second[n])
                pos_sample.append(pos_first[n])
                
            packetnums.append(int.from_bytes(bytes(pos_sample[0:2]), 'big'))
            timestamps.append(int.from_bytes(bytes(pos_sample[2:4]), 'big'))
            y1s.append(int.from_bytes(bytes(pos_sample[4:6]), 'big'))
            x1s.append(int.from_bytes(bytes(pos_sample[6:8]), 'big'))
            y2s.append(int.from_bytes(bytes(pos_sample[8:10]), 'big'))
            x2s.append(int.from_bytes(bytes(pos_sample[10:12]), 'big'))
            numpix1s.append(int.from_bytes(bytes(pos_sample[12:14]), 'big'))
            numpix2s.append(int.from_bytes(bytes(pos_sample[14:16]), 'big'))
            totalpixs.append(int.from_bytes(bytes(pos_sample[16:18]), 'big'))
            
            # the X and Y values are reversed piece-wise so lets switch the format from
            # packet #, video timestamp, y1, x1, y2, x2, numpix1, numpix2, total_pix, unused value
            # to
            # packet #, video timestamp, x1, y1, x2, y2, numpix1, numpix2, total_pix, unused value
            y1 = pos_sample[4:6]
            x1 = pos_sample[6:8]
            y2 = pos_sample[8:10]
            x2 = pos_sample[10:12]
            
            pos_sample[4:6] = x1
            pos_sample[6:8] = y1
            pos_sample[8:10] = x2
            pos_sample[10:12] = y2
            
            pos_sample = bytes(pos_sample)

    #         if len(position_data) < (trial_duration*50*2) +1:
            position_data.append(pos_sample)

    # Drop every second sample because pos data is double-counted in the .bin file
    position_data = position_data[::2]

    # save position data to csv
    pos_df = pd.DataFrame([packetnums, timestamps, x1s, x2s, y1s, y2s, numpix1s, numpix2s, totalpixs], 
                          index = ['Packet Number', 'Timestamps', 'X1', 'X2', 'Y1', 'Y2', 'Pixels LED 1', 'Pixels LED 2', 'Total Pixels'])
    pos_df = pos_df.iloc[:, ::2]
    pos_df = pos_df.set_axis(range(pos_df.shape[1]), axis = 1)
    pos_df.to_csv(f'{path}_pos.csv')

    # save position data to binary file
    with open(f'{path}.pos', 'wb') as f:
        for line in header:
            f.write(line.encode())
        for pos_sample in position_data:
            f.write(pos_sample)
        f.write('\r\ndata_end\r\n'.encode())

        f.close()
    