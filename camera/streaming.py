import io
from threading import Condition

# MJPEG 스트리밍을 위한 Output 클래스
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None    # MJPEG 이미지 데이터 저장하는 변수
        self.condition = Condition() # 촬영과 전송이 서로 충돌하지 않도록 방지(멀티스레드)
        # 이 객체는 한 스레드가 작업을 완료할 때까지 다른 스레드가 대기하도록 합니다.


    def write(self, buf):   # buf는 새로운 비디오프레임
        with self.condition:   # 조건 객체를 잠그는 역할을 합니다. 이 구문 내에서는 현재 스레드만 self.frame에 접근할 수 있습니다
            self.frame = buf
            self.condition.notify_all()    # 다른 스레드에게 새로운 프레임이 준비되었음을 알리는 역할
