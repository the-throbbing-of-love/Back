import pymysql
from dotenv import load_dotenv
import os

load_dotenv()   # .env파일에서 변수들을 가져와 os.environ에 넣어둔다.

ip = os.environ.get('IP')   # os.environ에서 값을 가져온다.
user = os.environ.get('USER')
password = os.environ.get('PASSWORD')
db = os.environ.get('DB')
print(ip, user, password, db)

class Round_db:
    def __init__(self):
        self.db = pymysql.connect(host=ip, user=user, password=password, db=db)
        self.cur = self.db.cursor()
        print("connect ok")

    def delete_round(self, id):
        try:
            sql = f"delete from Round where round_id={id}"
            self.cur.execute(sql)
            self.db.commit()
            return True
        except Exception as e:  # 모든 예외의 에러 메시지를 출력할 때는 Exception을 사용
            print('회차 삭제중 예외가 발생했습니다 : ', e)
            return False

    def create_round(self):
        try:
            sql = f"select max(Round_id) from Round;"
            self.cur.execute(sql)
            result = self.cur.fetchone()
            result = result[0]
            if result is None:
                result = 0
            # print(result)
            sql = f"insert into Round values({result+1}, 0, 0, '/home/huhon/visual_novel/visual_novel/static/images/round_{result+1}')"   # ./images/round_ 상대경로
            self.cur.execute(sql)
            self.db.commit()

            return {"success" : True, "next" : result + 1}
        except Exception as e:  # 모든 예외의 에러 메시지를 출력할 때는 Exception을 사용
            print('회차 생성중 예외가 발생했습니다 : ', str(e))
            return {"success" : False, "error" : '회차 생성중 예외가 발생했습니다 : ' + str(e)}

class BPM_db:
    def __init__(self):
        self.db = pymysql.connect(host=ip, user=user, password=password, db=db)
        self.cur = self.db.cursor()
        print("connect ok")
    def save_bpm(self, page_id, round_id, heart):
        try:
            sql=f"insert into Heart(page_id, round_id, heart) values({page_id}, {round_id}, {heart})"
            self.cur.execute(sql)
            self.db.commit()

            return {"success" : True}
        except Exception as e:  # 모든 예외의 에러 메시지를 출력할 때는 Exception을 사용
            print('심박수 저장중 예외가 발생했습니다 : ', str(e))
            return {"success" : False, "error" : '심박수 저장중 예외가 발생했습니다' + str(e)}
    def max_heart(self, round_id):
        sql = f"select max(heart), page_id from Heart where Round_id = {round_id};"
        self.cur.execute(sql)
        result = self.cur.fetchone()
        result = result[1]
        if result is None:
            return {"success" : False, "error" : '아직 심박수 정보가 없습니다. : ' + str(e)}
        else:
            return {"success" : True, "result" : result}
        


class face_AI:
    def __init__(self):
        self.db = pymysql.connect(host=ip, user=user, password=password, db=db)
        self.cur = self.db.cursor()
        print("connect ok")
    def save_analyze(self, round_id, page, angry, disgust, fear, happy, sad, surprise, neutral):
        try:
            sql = f"insert into Analyze_face(page_id, angry, disgust, fear, happy, sad, surprise, neutral, Round_id) values({page}, {angry}, {disgust}, {fear}, {happy}, {sad}, {surprise}, {neutral}, {round_id});"
            self.cur.execute(sql)
            self.db.commit()

            return {"success": True}
        except Exception as e:
            return {"success" : False, "error" : '감정분석 결과 저장중 예외가 발생했습니다' + str(e)}
    def max_happy(self, round_id):
        sql=f"select max(happy), page_id from Analyze_face where round_id={round_id};"
        self.cur.execute(sql)
        result = self.cur.fetchone()
        result = result[1]
        if result is None:
            return {"success" : False, "error" : '아직 감정분석 정보가 없습니다. : ' + str(e)}
        else:
            return {"success" : True, "result" : result}
            
class Image_db:
    def __init__(self):
        self.db = pymysql.connect(host=ip, user=user, password=password, db=db)
        self.cur = self.db.cursor()
        print("connect ok")
    def save_image(self, round_id, file_name, file_path):
        try:
            sql = f"insert into Image(round_id, file_name, file_path) values({round_id}, '{file_name}', '{file_path}')"
            self.cur.execute(sql)
            self.db.commit()

            return {"success": True}
        except Exception as e:
            return {"success" : False, "error" : '심박수 저장중 예외가 발생했습니다' + str(e)}
