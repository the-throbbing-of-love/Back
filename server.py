import io
import logging
import threading
from threading import Condition
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import time
import os
import shutil
from PIL import Image
from rembg import remove
import base64

from camera.streaming import StreamingOutput
from heart.pulsesensor import Pulsesensor
from model.visual_novel_db import Round_db, BPM_db, Image_db, face_AI

import eventlet
import socketio
from flask_socketio import SocketIO, send

# Flask 앱 생성
app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
round_db = Round_db()
bpm_db = BPM_db()
img_db = Image_db()
face_db = face_AI()

@app.route('/round/delete', methods=['DELETE'])
def round_delete():
    try:
        id = request.form['round_id']
        result = round_db.delete_round(id)
        if result:
            shutil.rmtree('./static/images/round_' + str(id), ignore_errors=True)
            return Response(status=204)
        else:
            return Response(status=500)
    except Exception as e:
        print("회차 삭제중 예외가 발생했습니다 :",e)
        return Response(status=500)

@app.route('/round/new-round', methods=['POST'])
def round_new():
    try:
        result = round_db.create_round()
        if result["success"]:
            os.mkdir('./static/images/round_' + str(result['next']))
            return jsonify({"new-round" : result["next"]}), 201
        else:
            return jsonify({"error" : result["error"]}), 500
    except Exception as e:
        print("회차 생성중 예외가 발생했습니다 :",e)
        return jsonify({"error": e}), 500

# Picamera2 설정
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))    # 카메라의 비디오 구성 설정
output = StreamingOutput()
picam2.start_recording(MJPEGEncoder(), FileOutput(output)) # 비디오 녹화모드 및 영상을 jpeg로 처리

# Flask 루트 경로
@app.route("/camera")
def camera():
    return render_template("camera.html")

@app.route("/cameraAI")
def cameraAI():
    return render_template("cameraAI.html")

@app.route("/camera/take-photo", methods=['POST'])
def save():
    try:
        round_id = request.form['round_id']
        scene = request.form['scene']
        file_name = scene + '.png'
        file_path = './static/images/round_' + round_id + '/'
        picam2.capture_file(file_path + file_name)
        result = img_db.save_image(round_id, file_name, file_path)

        input_file = file_path + file_name
        output_file = file_path + file_name

        img = Image.open(input_file)
        out = remove(img)
        background = None
        if scene == '3':
            background = Image.open('background1.png')
        elif scene == '4':
            background = Image.open('background2.png')
        elif scene == '5':
            background = Image.open('background3.png')

        # 배경 이미지 크기 맞추기 (필요시)
        background = background.resize(out.size)

        # 배경이 제거된 이미지를 RGBA 모드로 변환
        out = out.convert('RGBA')

        # 배경 이미지가 RGBA 모드로 변환되어야 함
        background = background.convert('RGBA')

        new_img = Image.alpha_composite(background, out)
        new_img.save(output_file)
        print(f"합성된 이미지를 '{output_file}'에 저장했습니다.")
        if result['success']:
            print("저장완료")
            return render_template("close.html", path=output_file)
        else:
            print("사진 저장중 예외가 발생했습니다 :", result["error"])
            return Response(status=500)
    except Exception as e:
        print("사진 편집중 예외가 발생했습니다 :",e)
        return Response(status=500)

# MJPEG 스트림을 반환하는 경로
@app.route("/stream.mjpg")
def stream():
    def generate():    # MJPEG 스트리밍을 위한 프레임 생성기
        while True:
            with output.condition:
                output.condition.wait()    # 프래임 준비될때 까지 기다리기
                frame = output.frame
            yield (b'--FRAME\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame)).encode() + b'\r\n\r\n' +
                   frame + b'\r\n')    # 새로운 MJPEG 프레임을 클라이언트에게 전송합니다.
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=FRAME')
    # 클라이언트에게 MJPEG 스트리밍 전달, multipart/x-mixed-replace는 비디오 스트리밍에서 여러 개의 이미지를 연속적으로 전송할 때 사용됩니다.

heart_bit = [80 for i in range(5)]

p = Pulsesensor()
p.startAsyncBPM()

count = 0
def measure_heartbeat():
    global heart_bit, count
    try:
        while True:
            bpm = p.BPM
            if bpm > 0:
                print("BPM: %d" % bpm)
            else:
                print("No Heartbeat found")
                bpm = sum(heart_bit) / 5
            heart_bit[count] = bpm
            count = (count+1)%5
        
            time.sleep(1)
    except:
        p.stopAsyncBPM()

def heart_error():
    global heart_bit, count
    beforeBpm = heart_bit[count-5]
    rising = 0
    print("heart_bit", heart_bit)
    for bpm in range(count-4, count):
        if heart_bit[bpm] > beforeBpm:
            rising += 1
        elif heart_bit[bpm] < beforeBpm:
            rising -= 1
        beforeBpm = heart_bit[bpm]
    return rising > 0

@app.route("/heart/measurement", methods=['POST'])
def heart():
    global heart_bit, count
    round_id = request.form['round_id']
    page = request.form['page']
    heart = heart_bit[count-1]
    error = heart_error()
    result = bpm_db.save_bpm(page, round_id, heart)
    if result['success']:
        return jsonify({"heart" : heart, "rising" : error}), 201
    else:
        return jsonify({"error" : result["error"]}), 500

faceAI = None

@socketio.on('faceAI')
def result(result):
    global faceAI
    if len(result)!=0:
        faceAI = result
    else:
        print("faceAI is NULL")

@app.route("/AI-analyze/face", methods=['POST'])
def faceAI_result():
    round_id = request.form['round_id']
    page = request.form['page']
    result = {
        "angry" : f"{faceAI[0]['expressions']['angry']:.8f}",
        "disgust" : f"{faceAI[0]['expressions']['disgusted']:.8f}",
        "fear" : f"{faceAI[0]['expressions']['fearful']:.8f}",
        "happy" : f"{faceAI[0]['expressions']['happy']:.8f}",
        "sad" : f"{faceAI[0]['expressions']['sad']:.8f}",
        "surprise" : f"{faceAI[0]['expressions']['surprised']:.8f}",
        "neutral" : f"{faceAI[0]['expressions']['neutral']:.8f}"
    }
    response = face_db.save_analyze(round_id, page, faceAI[0]['expressions']['angry'], faceAI[0]['expressions']['disgusted'], faceAI[0]['expressions']['fearful'], faceAI[0]['expressions']['happy'], faceAI[0]['expressions']['sad'], faceAI[0]['expressions']['surprised'], faceAI[0]['expressions']['neutral'])
    if response['success']:
        return jsonify(result), 201
    else:
        return jsonify({"error" : response["error"]}), 500

@app.route("/history/photo", methods=['GET'])
def history():
    round_id = request.args.get('round_id')
    scene = request.args.get('scene')
    try:
        file_name = scene + '.png'
        file_path = './images/round_' + round_id + '/'
        return send_from_directory(file_path, file_name), 201
    except Exception as e:
        print("사진 전송중 예외가 발생했습니다 : ",e)
        return jsonify({"error" : str(e)}), 500

@app.route("/history/biggest-heart", methods=["GET"])
def max_heart():
    round_id = request.args.get('round_id')
    try:
        result = bpm_db.max_heart(round_id)
        if result['success']:
            return jsonify({"heart-page" : result['result']})
        else:
            return jsonify({"error" : e}), 400
    except Exception as e:
        print("최대 심박수 조회중 예외가 발생했습니다 : ",e)
        return jsonify({"error" : str(e)}), 500

@app.route("/history/happiest-moment", methods=["GET"])
def max_happy():
    round_id = request.args.get('round_id')
    try:
        result = face_db.max_happy(round_id)
        if(result['success']):
            return jsonify({"happy-page" : result['result']})
        else:
            return jsonify({"error" : e}), 400
    except Exception as e:
        print("최대 행복페이지 조회중 예외가 발생했습니다 : ",e)
        return jsonify({"error" : str(e)}), 500

@app.route("/history", methods=["GET"])
def total_history():
    round_id = request.args.get('round_id')
    try:
        return render_template("history.html", round_id = round_id)
    except Exception as e:
        print("모든 추억 회상중 예외가 발생했습니다 : ",e)
        return jsonify({"error" : str(e)}), 500

# 앱 실행
if __name__ == "__main__":
    heartbeat_thread = threading.Thread(target=measure_heartbeat)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()
    try:
        socketio.run(app, host="0.0.0.0", port=8000, use_reloader=False)
    finally:
        picam2.stop_recording()
        p.stopAsyncBPM()
        print("Resources released.")
