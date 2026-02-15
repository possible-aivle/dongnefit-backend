import os
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# 티스토리 작성 클래스
class TistoryWriter:
    # 초기화
    def __init__(self, tistory_id, tistory_password):
        self.tistory_id = tistory_id
        self.tistory_password = tistory_password
        self.driver = webdriver.Chrome()

    # 로그인
    def login(self):
        # 티스토리 로그인 페이지 이동
        self.driver.get("https://www.tistory.com/auth/login")

        # 카카오 로그인 버튼 클릭
        kakao_login_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "txt_login"))
        )
        kakao_login_button.click()

        # 이메일 입력
        email_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "loginId"))
        )
        email_input.send_keys(self.tistory_id)

        # 비밀번호 입력
        password_input = self.driver.find_element(By.NAME, "password")
        password_input.send_keys(self.tistory_password)

        # 로그인 버튼 클릭
        login_button = self.driver.find_element(
            By.CSS_SELECTOR, 'button[type="submit"]'
        )
        login_button.click()

        # 로그인 완료 대기
        WebDriverWait(self.driver, 15).until(EC.url_contains("tistory.com"))
        time.sleep(5)
        print("✅ 로그인 완료")

    # 게시글 작성
    def write_post(self, blog_title, blog_content, category_name, hashtags, image_paths=None):
        """
        티스토리에 게시글을 작성합니다.

        Args:
            blog_title (str): 블로그 제목
            blog_content (str): 블로그 본문 ({{IMAGE:경로}} 플레이스홀더 포함 가능)
            category_name (str): 카테고리 이름
            hashtags (list): 해시태그 리스트
            image_paths (list, optional): 업로드할 이미지 파일 경로 리스트
        """
        # 티스토리 관리 페이지 이동
        self.driver.get("https://wodongtest.tistory.com/manage")

        # 글쓰기 버튼 클릭
        write_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "글쓰기"))
        )
        write_button.click()

        try:
            if WebDriverWait(self.driver, 3).until(EC.alert_is_present()):
                alert = self.driver.switch_to.alert
                alert.dismiss()
        except TimeoutException:
            pass

        # 마크다운 모드 버튼 클릭
        mode_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "editor-mode-layer-btn-open"))
        )
        mode_button.click()

        # 마크다운 모드 선택
        markdown_option = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "editor-mode-markdown"))
        )
        markdown_option.click()
        print("✅ 마크다운 모드 선택")

        # 알림창 확인
        WebDriverWait(self.driver, 5).until(EC.alert_is_present())
        alert = self.driver.switch_to.alert
        alert.accept()

        # 제목 입력
        title_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "post-title-inp"))
        )
        title_input.clear()
        title_input.send_keys(blog_title)
        print("✅ 제목 입력 완료")

        # 먼저 플레이스홀더가 포함된 본문 입력
        cm_div = self.driver.find_element(
            By.CSS_SELECTOR, ".CodeMirror.cm-s-tistory-markdown.CodeMirror-wrap"
        )
        self.driver.execute_script(
            """
            var cm = arguments[0].CodeMirror;
            cm.setValue(arguments[1]);
            cm.refresh();
            cm.save();
            cm.focus();
            cm.display.input.textarea.blur();
            cm.display.input.textarea.focus();
            var event = new Event('input', { bubbles: true, cancelable: true });
            cm.display.input.textarea.dispatchEvent(event);
        """,
            cm_div,
            blog_content,  # 플레이스홀더가 포함된 원본 내용
        )
        cm_div.click()
        time.sleep(0.5)
        text_area = cm_div.find_element(By.CSS_SELECTOR, "textarea")
        text_area.send_keys(".")
        self.driver.execute_script("arguments[0].CodeMirror.save();", cm_div)
        print("✅ 본문 입력 완료 (플레이스홀더 포함)")

        # 이미지 업로드 및 본문 내 플레이스홀더 치환
        if image_paths:
            print(f"🖼️ {len(image_paths)}개의 이미지 업로드 시작...")
            import re
            
            for image_path in image_paths:
                # 이미지 업로드
                uploaded_url = self.upload_image(image_path)
                
                if uploaded_url:
                    # 현재 에디터 내용 가져오기
                    current_content = self.driver.execute_script(
                        "return arguments[0].CodeMirror.getValue();", cm_div
                    )
                    
                    # 플레이스홀더에서 alt 텍스트 추출
                    # 형식: {{IMAGE:경로}} 또는 {{IMAGE:경로|alt텍스트}}
                    if "|" in image_path:
                        # alt 텍스트가 포함된 경우 (새 형식)
                        actual_path = image_path.split("|")[0]
                        alt_text = image_path.split("|", 1)[1] if "|" in image_path else "블로그 이미지"
                        placeholder = f"{{{{IMAGE:{image_path}}}}}"
                    else:
                        # alt 텍스트가 없는 경우 (기존 형식)
                        actual_path = image_path
                        alt_text = "블로그 이미지"
                        placeholder = f"{{{{IMAGE:{image_path}}}}}"
                    
                    # 이미지를 가운데 정렬하고 스타일 추가 (SEO 친화적인 alt 텍스트 사용)
                    image_markdown = f'<div style="text-align: center; margin: 20px 0;">\n  <img src="{uploaded_url}" alt="{alt_text}" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">\n</div>'
                    updated_content = current_content.replace(placeholder, image_markdown)
                    
                    # 업데이트된 내용을 에디터에 다시 설정
                    self.driver.execute_script(
                        """
                        var cm = arguments[0].CodeMirror;
                        cm.setValue(arguments[1]);
                        cm.save();
                        """,
                        cm_div,
                        updated_content
                    )
                    print(f"✅ 이미지 플레이스홀더 치환 완료: {image_path}")
                else:
                    # 업로드 실패 시 플레이스홀더 제거
                    current_content = self.driver.execute_script(
                        "return arguments[0].CodeMirror.getValue();", cm_div
                    )
                    placeholder = f"{{{{IMAGE:{image_path}}}}}"
                    updated_content = current_content.replace(placeholder, "")
                    self.driver.execute_script(
                        """
                        var cm = arguments[0].CodeMirror;
                        cm.setValue(arguments[1]);
                        cm.save();
                        """,
                        cm_div,
                        updated_content
                    )
                    print(f"⚠️ 이미지 업로드 실패, 플레이스홀더 제거: {image_path}")
            
            print(f"✅ {len(image_paths)}개의 이미지 처리 완료")

        # 카테고리 선택
        self.select_category(category_name)

        # 해시태그 입력
        self.add_hashtags(hashtags)

        # 게시글 발행
        self.publish_post()

        time.sleep(1)

    def upload_image(self, image_path: str) -> str:
        """
        로컬 이미지를 티스토리 에디터에 업로드하고 업로드된 이미지 URL을 반환합니다.

        Args:
            image_path (str): 업로드할 로컬 이미지 파일 경로

        Returns:
            str: 업로드된 이미지의 티스토리 URL (업로드 실패 시 빈 문자열)
        """
        if not os.path.exists(image_path):
            print(f"❌ 이미지 파일이 존재하지 않습니다: {image_path}")
            return ""

        try:
            # 절대 경로로 변환
            abs_image_path = os.path.abspath(image_path)
            print(f"📤 이미지 업로드 시작: {abs_image_path}")
            
            # 1. 먼저 CodeMirror가 있는 컨텍스트 찾기 (가장 중요)
            print("🔍 CodeMirror 에디터 찾는 중...")
            cm_div = None
            current_context = "메인"
            
            # 메인 컨텍스트에서 시도
            try:
                self.driver.switch_to.default_content()
                cm_div = self.driver.find_element(
                    By.CSS_SELECTOR, ".CodeMirror.cm-s-tistory-markdown.CodeMirror-wrap"
                )
                print("✅ CodeMirror 발견: 메인 컨텍스트")
                current_context = "메인"
            except:
                # iframe들에서 시도
                print("⚠️ 메인 컨텍스트에서 CodeMirror 없음, iframe 확인 중...")
                self.driver.switch_to.default_content()
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                print(f"📋 {len(iframes)}개의 iframe 발견")
                
                for i, iframe in enumerate(iframes):
                    try:
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(iframe)
                        cm_div = self.driver.find_element(
                            By.CSS_SELECTOR, ".CodeMirror.cm-s-tistory-markdown.CodeMirror-wrap"
                        )
                        print(f"✅ CodeMirror 발견: iframe[{i}]")
                        current_context = f"iframe[{i}]"
                        break
                    except:
                        continue
            
            if not cm_div:
                print("❌ CodeMirror 에디터를 찾을 수 없습니다.")
                raise Exception("CodeMirror 에디터를 찾을 수 없습니다")
            
            # 2. 현재 에디터 내용 저장 (비교를 위해)
            before_content = self.driver.execute_script(
                "return arguments[0].CodeMirror.getValue();", cm_div
            )
            
            if not before_content:
                before_content = ""
            
            print(f"📝 현재 에디터 내용 길이: {len(before_content)}자")
            
            # 3. 메인 컨텍스트로 돌아가서 첨부 버튼 찾기
            self.driver.switch_to.default_content()
            
            print("🔍 첨부 버튼 찾는 중...")
            # JavaScript로 직접 버튼 찾기 및 클릭
            try:
                button_clicked = self.driver.execute_script("""
                    var btn = document.getElementById('attach-layer-btn');
                    if (btn) {
                        btn.click();
                        return true;
                    }
                    return false;
                """)
                if button_clicked:
                    print("✅ 첨부 버튼 클릭 완료 (JavaScript)")
                    time.sleep(1)
                else:
                    print("⚠️ 첨부 버튼을 찾을 수 없음 (JavaScript)")
            except Exception as e:
                print(f"⚠️ 첨부 버튼 클릭 실패: {e}")
            
            # 4. 파일 input 찾기 - JavaScript로 직접 접근
            print("🔍 파일 입력 요소 찾는 중...")
            try:
                # JavaScript로 파일 input 존재 확인
                input_exists = self.driver.execute_script("""
                    return document.getElementById('attach-image') !== null;
                """)
                
                if input_exists:
                    print("✅ 파일 입력 요소 발견 (JavaScript): #attach-image")
                    
                    # Selenium으로 파일 input 찾기
                    file_input = self.driver.find_element(By.ID, "attach-image")
                else:
                    print("❌ 파일 입력 요소를 찾을 수 없습니다")
                    raise Exception("파일 입력 요소 없음")
                    
            except Exception as e:
                print(f"❌ 파일 입력 요소를 찾을 수 없습니다: {e}")
                # Base64 fallback
                print("💡 대안: base64 인코딩 사용...")
                import base64
                with open(abs_image_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode()
                    data_url = f"data:image/png;base64,{img_data}"
                    return data_url
            
            # 5. 파일 경로 전송
            file_input.send_keys(abs_image_path)
            print("✅ 파일 경로 전송 완료")
            
            # 6. 업로드 완료 대기
            print("⏳ 이미지 업로드 중...")
            time.sleep(4)
            
            # 7. CodeMirror가 있던 컨텍스트로 다시 전환
            if current_context != "메인":
                iframe_index = int(current_context.split("[")[1].split("]")[0])
                self.driver.switch_to.default_content()
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                self.driver.switch_to.frame(iframes[iframe_index])
            else:
                self.driver.switch_to.default_content()
            
            # 8. 업로드 후 에디터 내용 가져오기
            after_content = self.driver.execute_script(
                "return arguments[0].CodeMirror.getValue();", cm_div
            )
            
            if not after_content:
                after_content = ""
            
            print(f"📝 업로드 후 에디터 내용 길이: {len(after_content)}자")
            
            # 9. 마크다운 이미지 문법에서 URL 추출
            import re
            image_pattern = r'!\[.*?\]\((https?://[^)]+)\)'
            
            before_matches = set(re.findall(image_pattern, before_content))
            after_matches = set(re.findall(image_pattern, after_content))
            
            # 새로 추가된 이미지 URL 찾기
            new_images = after_matches - before_matches
            
            if new_images:
                uploaded_url = list(new_images)[0]
                print(f"✅ 이미지 업로드 완료: {uploaded_url}")
                
                # 업로드된 이미지를 에디터에서 제거 (나중에 올바른 위치에 삽입하기 위함)
                for match in re.finditer(image_pattern, after_content):
                    if match.group(1) == uploaded_url:
                        cleaned_content = after_content.replace(match.group(0), "")
                        self.driver.execute_script(
                            """
                            var cm = arguments[0].CodeMirror;
                            cm.setValue(arguments[1]);
                            cm.save();
                            """,
                            cm_div,
                            cleaned_content
                        )
                        break
                
                # 메인 컨텍스트로 복귀
                self.driver.switch_to.default_content()
                return uploaded_url
            else:
                print("❌ 업로드된 이미지 URL을 찾을 수 없습니다.")
                print(f"이전 이미지 수: {len(before_matches)}, 이후 이미지 수: {len(after_matches)}")
                
                # Base64 fallback
                print("💡 대안: base64 인코딩 사용...")
                import base64
                with open(abs_image_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode()
                    data_url = f"data:image/png;base64,{img_data}"
                    self.driver.switch_to.default_content()
                    return data_url
                
        except Exception as e:
            print(f"❌ 이미지 업로드 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            
            # 메인 컨텍스트로 복귀
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            
            # Base64 fallback
            try:
                print("💡 대안: base64 인코딩 사용...")
                import base64
                abs_path = os.path.abspath(image_path)
                with open(abs_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode()
                    data_url = f"data:image/png;base64,{img_data}"
                    return data_url
            except Exception as e2:
                print(f"❌ Base64 인코딩도 실패: {e2}")
                return ""

    # 카테고리 선택
    def select_category(self, category_name):
        category_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "category-btn"))
        )
        category_button.click()

        # 전체 카테고리 아이템 div 들을 가져옴
        category_list = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div[id^='category-item-']")
            )
        )

        # 카테고리 선택
        found = False
        for item in category_list:
            # 각 카테고리의 실제 이름은 aria-label 속성에 존재
            label = item.get_attribute("aria-label")
            if label:
                label = label.strip()
                if category_name.strip() == label or category_name.strip() in label:
                    item.click()
                    print(f"✅ '{label}' 카테고리 선택 완료")
                    found = True
                    break

        if not found:
            # 카테고리 없음 선택
            no_category_item = self.driver.find_element(
                By.CSS_SELECTOR, "div[aria-label='카테고리 없음']"
            )
            no_category_item.click()
            print("⚠ 지정된 카테고리가 없어 '카테고리 없음'으로 설정")
        time.sleep(1)

    # 해시태그 입력
    def add_hashtags(self, hashtags):
        tag_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "tagText"))
        )
        for tag in hashtags:
            tag_input.clear()
            tag_input.send_keys(tag)
            tag_input.send_keys("\ue004")  # TAB 키 입력 (엔터 대신)
            time.sleep(0.3)
        print("✅ 해시태그 입력 완료")

    # 게시글 발행
    def publish_post(self):
        # 게시글 발행 버튼 클릭
        publish_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "publish-layer-btn"))
        )
        publish_button.click()

        # 게시글 발행 버튼 클릭
        publish_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, "publish-btn"))
        )
        publish_button.click()
        print("✅ 게시글 발행 완료")

    # 브라우저 종료
    def close(self):
        self.driver.quit()
