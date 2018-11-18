# -*- coding: utf-8 -*-
#
#   Copyright 2017-18 Nick Boultbee
#   This file is part of squeeze-alexa.
#
#   squeeze-alexa is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   See LICENSE for full license

from squeezealexa.transport.base import Transport
from squeezealexa.utils import print_d

REAL_FAVES = """title%3AFavorites id%3A0
name%3AChilled%20Jazz type%3Aaudio
url%3Afile%3A%2F%2F%2Fvolume1%2Fplaylists%2FChilled%2520Jazz.m3u isaudio%3A1
hasitems%3A0 id%3A1
name%3APiano-friendly type%3Aaudio
url%3Afile%3A%2F%2F%2Fvolume1%2Fplaylists%2FPiano-friendly.m3u isaudio%3A1
hasitems%3A0
count%3A18""".replace('\n', ' ')

A_REAL_STATUS = """
 player_name%3AStudy player_connected%3A1 player_ip%3A'
 192.168.1.35%3A51196 power%3A1 signalstrength%3A0 mode%3Aplay
 time%3A23.9624403781891 rate%3A1 duration%3A358.852 can_seek%3A1
 sync_master%3A00%3A04%3A20%3A17%3A5c%3A94
 mixer%20volume%3A98 playlist%20repeat%3A0
 playlist%20shuffle%3A1 playlist%20mode%3Aoff
 seq_no%3A0 playlist_cur_index%3A20
 playlist_timestamp%3A1493318044.34369 playlist_tracks%3A62
 digital_volume_control%3A1 playlist%20index%3A20 id%3A134146
 title%3AConcerto%20No.%2023%20in%20A%20Major%2C%20K.%20488%3A%20Adagio
 genre%3AJazz artist%3AJacques%20Loussier%20Trio
 album%3AMozart%20Piano%20Concertos%2020%2F23
 duration%3A358.852 playlist%20index%3A21 id%3A134174
 title%3AI%20Think%2C%20I%20Love genre%3AJazz
 artist%3AJamie%20Cullum album%3AThe%20Pursuit duration%3A255.906
""".lstrip().replace('\n', '')

NO_ARTIST_STATUS = """player_name%3AUpstairs%20Music
 player_connected%3A1 player_ip%3A192.168.1.35%3A45672 power%3A0
 signalstrength%3A78 mode%3Astop remote%3A1 current_title%3ABBC%20Radio%204
 time%3A0 rate%3A1 mixer%20volume%3A75 playlist%20repeat%3A0
 playlist%20shuffle%3A2 playlist%20mode%3Aoff seq_no%3A0 playlist_cur_index%3A0
 playlist_timestamp%3A1539889230.96449 playlist_tracks%3A1
 digital_volume_control%3A1 remoteMeta%3AHASH(0xef71c70) playlist%20index%3A0
 id%3A-230948072 title%3ABBC%20Radio%204""".replace('\n', '')

FAKE_LENGTH = 358.852


class FakeTransport(Transport):

    def __init__(self, fake_name='fake', fake_id='12:34',
                 fake_status=A_REAL_STATUS, fake_server_status=None):
        self.hostname = 'localhost'
        self.port = 0
        self.failures = 0
        self.is_connected = False
        self.player_name = fake_name
        self.player_id = fake_id
        self.all_input = ""
        self._status = fake_status
        self._server_status = fake_server_status

    def communicate(self, data, wait=True):
        self.all_input += data
        stripped = data.rstrip('\n')
        if data.startswith('serverstatus'):
            if self._server_status:
                return self._server_status
            else:
                return ('{orig} player%20count:1 playerid:{pid} connected:1 '
                        'name:{name}\n'
                        .format(orig=stripped, name=self.player_name,
                                pid=self.player_id))

        elif ' status ' in stripped:
            print_d("Faking player status...")
            return stripped + self._status
        elif 'login ' in stripped:
            return 'login %s ******' % stripped.split()[1].replace(' ', '%20')
        elif ' time ' in data:
            return '%s %.3f' % (stripped.rstrip('?'), FAKE_LENGTH)
        elif 'favorites items ' in data:
            return stripped + REAL_FAVES
        return stripped + ' OK\n'

    @property
    def details(self):
        return "{hostname}:{port}".format(**self.__dict__)
