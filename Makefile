# 10円玉の中の平等院
#   make all      鳳凰堂のシーン → 奥行き画像 → 10円玉の面 → 10円玉のシーン → 音（数分）
#   make test     10円玉と鳳凰堂の要所を半分の解像度で描く（数分）
#   make render   本番（鳳凰堂 216 コマ＋10円玉 168 コマ。M5 の Mac で約 1 時間）
#   make video    つないで build/juuen.mp4 に
#
# もとの「CAD 図面 → Blender」20 秒の動画は make byodoin-render / make byodoin-video

PYTHON  ?= python3
BLENDER ?= blender

.PHONY: all dxf dxf-preview scroll audio title scene depth face coin juuen-audio test camera render video \
        byodoin-test byodoin-render byodoin-video clean

all: scene depth face coin juuen-audio

depth: scene
	$(BLENDER) -b build/byodoin.blend -P tools/relief_depth.py

face: depth
	$(PYTHON) coin/make_face.py

coin: face
	$(BLENDER) -b --factory-startup -P coin/build_coin.py

juuen-audio:
	$(PYTHON) sound/juuen_audio.py

test:
	$(BLENDER) -b build/coin.blend -P tools/test_frames.py -- 1,75,130,168 50
	$(BLENDER) -b build/byodoin.blend -P tools/building_shot.py -- relief 1 1
	$(BLENDER) -b build/byodoin.blend -P tools/shot.py -- 480 build/test/building_end.png 170 0 9 0 0 8.4 40 50

render:
	tools/render_juuen.sh

video:
	$(PYTHON) finish/compose_juuen.py

dxf:
	$(PYTHON) cad/make_dxf.py

dxf-preview: dxf
	$(PYTHON) cad/preview.py

scroll:
	$(PYTHON) drawing/make_scroll.py

audio:
	$(PYTHON) sound/make_audio.py

title:
	$(PYTHON) finish/make_title.py

scene: scroll
	$(BLENDER) -b --factory-startup -P scene/build.py

byodoin-test:
	$(BLENDER) -b build/byodoin.blend -P tools/test_frames.py -- 61,150,250,400,504 50

camera:
	$(BLENDER) -b build/byodoin.blend -P tools/check_camera.py

byodoin-render:
	tools/render_chunks.sh

byodoin-video: audio title
	finish/compose.sh

clean:
	rm -rf build
