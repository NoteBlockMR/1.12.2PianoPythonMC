from mcpi.minecraft import Minecraft
import time
import mido
from mido import MidiFile
import threading
from mcpi import block

# 마인크래프트 연결
mc = Minecraft.create()
player_pos = mc.player.getTilePos()
base_x, base_y, base_z = player_pos.x, player_pos.y, player_pos.z

# 파티클 설정 (note_on/off 별 속도, 수명, 모션)
particle_config = {
    "on": {"motion": (0, 0, 0), "speed": 0.3, "lifetime": 1.5, "spread": 0.3},
    "off": {"motion": (0.5, 1.0, 0.5), "speed": 1.5, "lifetime": 0.3, "spread": 1.0}
}

# 건반 색상 매핑 (흰색/검정)
instrument_color = {
    0: (0.9, 0.9, 0.9),  # 흰색 건반
    15: (0.1, 0.1, 0.1)   # 검정 건반
}

# 1. 피아노 건반 초기화 (3옥타브)
def create_piano_3_octave():
    white_keys = [0, 2, 4, 5, 7, 9, 11]  # 온음 건반 위치
    for octave in range(3):  # 3옥타브 (C4 ~ C6)
        for i in range(12):  # 12음계
            x = base_x + (octave * 12) + i
            if i in white_keys:
                mc.setBlock(x, base_y, base_z, block.WOOL.id, 0)  # 흰색
            else:
                mc.setBlock(x, base_y, base_z, block.WOOL.id, 15)  # 검정

# 2. 파티클 생성 함수
def spawn_particles(x, data, is_note_on):
    color = instrument_color.get(data, (1, 1, 1))
    config = particle_config["on"] if is_note_on else particle_config["off"]
    
    # 파티클 명령어 (건반 위 1.2블록 높이에서 생성)
    mc.postToChat(
        f"/particleex conditional minecraft:dust {x + 0.5} {base_y + 1.2} {base_z + 0.5} "
        f"{color[0]} {color[1]} {color[2]} 1 "  # RGB 색상
        f"{config['motion'][0]} {config['motion'][1]} {config['motion'][2]} "  # 모션
        f"{config['spread']} {config['spread']} {config['spread']} "  # 확산
        f"'abs(x) <= 0.5 & abs(y) <= 0.5 & abs(z) <= 0.5' "  # 조건
        f"{config['lifetime']} 15 0 {config['speed']}"  # 수명, 개수, 속도
    )

# 3. MIDI 연주 시스템
class MidiPlayer:
    def __init__(self, midi_file):
        self.midi = MidiFile(midi_file)
        self.note_to_x = {note: base_x + (note - 60) for note in range(36, 84)}
        self.active_notes = {}  # 활성화된 노트 추적

    def play_note(self, note, velocity):
        if (x := self.note_to_x.get(note)):
            data = mc.getBlockWithData(x, base_y, base_z).data
            self.active_notes[note] = data
            spawn_particles(x, data, True)  # note_on 파티클
            mc.setBlock(x, base_y, base_z, block.GOLD_BLOCK.id)  # 건반 누름
            mc.postToChat(f"/playsound piano.{note} @a ~ ~ ~ 1 1")  # 사운드

    def stop_note(self, note):
        if (x := self.note_to_x.get(note)) and (data := self.active_notes.pop(note, None)):
            spawn_particles(x, data, False)  # note_off 파티클
            mc.setBlock(x, base_y, base_z, block.WOOL.id, data)  # 건반 복원

    def start_playback(self):
        for msg in self.midi.play():
            if msg.type == 'note_on':
                if msg.velocity > 0:
                    threading.Thread(target=self.play_note, args=(msg.note, msg.velocity)).start()
                else:
                    threading.Thread(target=self.stop_note, args=(msg.note,)).start()
            elif msg.type == 'note_off':
                threading.Thread(target=self.stop_note, args=(msg.note,)).start()

# 4. 메인 실행
if __name__ == "__main__":
    create_piano_3_octave()  # 피아노 건반 생성
    player = MidiPlayer("your_song.mid")  # MIDI 파일 경로 지정
    
    # MIDI 재생 스레드 시작
    midi_thread = threading.Thread(target=player.start_playback)
    midi_thread.start()
