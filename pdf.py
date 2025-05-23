import streamlit as st
from PIL import Image
import numpy as np
from io import BytesIO
import base64
import os
import traceback
import time
from threading import Lock
import schedule

#PDF
import fitz  # PyMuPDF
import io
import json 
import json5
from statistics import mode

#LLM
import os
from openai import OpenAI
scan_lock = Lock()

st.set_page_config(layout="wide", page_title="PDF Table of Contents (TOC) Intelligent Generator")

st.write("## PDF Table of Contents (TOC) Intelligent Generator")
pdf_text = st.sidebar.empty()
pdf_text.write(":dog: Try uploading a PDF:")
status_text = st.sidebar.empty()
st.sidebar.write("## Upload and download :gear:")


# 新增：配置文件路径定义
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config() -> dict:
    """加载本地配置文件"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.sidebar.warning(f"加载配置失败: {str(e)}，将使用默认配置")
    return {}

def save_config(config: dict) -> None:
    """保存配置到本地文件"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        st.sidebar.success("配置已保存到本地文件")
    except Exception as e:
        st.sidebar.error(f"保存配置失败: {str(e)}")

# 加载上次保存的配置
saved_config = load_config()

st.sidebar.write("## 模型配置 :robot_face:")

# 自定义网址输入（带配置记忆）
custom_base_url = st.sidebar.text_input(
    "自定义API网址",
    placeholder="输入模型API的基础URL（如https://api.example.com/v1）",
    value=saved_config.get("custom_base_url", ""),  # 加载上次输入
)

model_detoc = st.sidebar.text_input(
    "model_detoc",
    placeholder="输入调用的模型",
    value=saved_config.get("model_detoc", ""),  # 加载上次输入
)

model_exinfo = st.sidebar.text_input(
    "model_exinfo",
    placeholder="输入调用的模型",
    value=saved_config.get("model_exinfo", ""),  # 加载上次输入
)

model_text = st.sidebar.text_input(
    "model_text",
    placeholder="输入调用的模型",
    value=saved_config.get("text", ""),  # 加载上次输入
)

# API Key输入（带配置记忆）
api_key = st.sidebar.text_input(
    "输入API Key",
    type="password",
    value=saved_config.get("api_key", ""),  # 加载上次输入（注意：密码明文存储有安全风险，生产环境需加密）
    help="请输入对应模型服务商的API Key（阿里云需开通DashScope服务，OpenAI需有效API Key）"
)

# 新增：保存配置按钮
if st.sidebar.button("💾 保存当前配置"):
    current_config = {
        "custom_base_url": custom_base_url,
        "model_detoc": model_detoc,
        "model_exinfo": model_exinfo,
        "api_key": api_key
    }
    save_config(current_config)

base_url = custom_base_url  # 自定义网址
    
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)


def llm_drift(image)-> bool:

    # 将PIL.Image转换为base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    try:
        completion = client.chat.completions.create(
            model=model_exinfo,  # 此处以qwen-vl-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            messages=[
                {"role": "system", "content": """请精确识别页面中的标题，包括但不限于以下格式：
                1. 章节标题（如'第一章'、'第1章'、'Chapter 1'）
                2. 小节标题（如'1.1'、'1.1.1'）
                3. 其他层级标题（如'A.'、'(1)'等）
                输出要求：
                1. 以JSON数组格式返回，每个元素包含'title'和'pno'字段，如：
                [{"title": "第一章 xxx", "pno": 1}, {"title": "1.1 xxx", "pno": 1}]
                2. 'pno'表示该页面的页码，'title'表示标题内容
                3. 只返回当前页面的标题和页码信息，不要解释或添加额外内容，以数组形式返回，注意返回的页码是int类型，如果该页面没有标题，那么就返回空数组"""},
                {"role": "user","content": [
                    {"type": "image_url","image_url": {"url": f"data:image/png;base64,{img_base64}" }}
                    ]}]
            )
        print(completion)
        raw_response = completion.choices[0].message.content
        print(raw_response)
        cleaned_response = raw_response.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            import json5  # 需要安装json5库
            return json5.loads(cleaned_response)    
    except Exception as e:
        print(f"目录信息提取失败: {str(e)}")
        print(f"原始响应内容: {raw_response}")  # 添加错误日志
        return []  

def llm_pdf_name(image)-> bool:

    # 将PIL.Image转换为base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    completion = client.chat.completions.create(
        model=model_detoc,  # 此处以qwen-vl-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=[
            {"role": "system", "content":  """接下来会给你发送一张书籍封面的图片，请你给出这本书的书面，只要书名就行，不要解释，不要输出其他内容，不要书名号"""},

            {"role": "user","content": [
                {"type": "image_url","image_url": {"url": f"data:image/png;base64,{img_base64}" }}
                ]}]
        )
    
    return completion.choices[0].message.content

def llm_is_toc(image)-> bool:

    # 将PIL.Image转换为base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    completion = client.chat.completions.create(
        model=model_detoc,  # 此处以qwen-vl-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=[
            {"role": "system", "content":  """Analyze whether the given image is a table of contents page in a book. 
                Return True if it is a table of contents page that must contains chapter/section titles aligned with page numbers, and return False if it's not."""},

            {"role": "user","content": [
                {"type": "image_url","image_url": {"url": f"data:image/png;base64,{img_base64}" }}
                ]}]
        )
    
    return completion.choices[0].message.content.lower()== "true"

def llm_extract_toc_info(image: Image.Image,toc) -> list:

    # 将图像转换为base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    # 构建prompt
    result_schema = """{
        [{"level": int,"title": "str","pno": int}]
    }"""
    prompt = f"""请从目录页图像中提取结构化信息，要求：
    1. 当前已识别目录结构如下（仅参考,只需要输出当前目录页的目录信息）：
    {json.dumps(toc, indent=2, ensure_ascii=False)}
    2. 识别目录中的层级关系（通过缩进或标题编号判断）,如:第n章层级是1,第n节层级是2,1.1层级是2,1.1.1层级是3,1.1.1.1层级是4等等,前面的示例仅供参考，可以根据上下文进行判断
    3. 提取每个条目标题和对应页码,如果有些标题没有页码,那么就跳过没有对应页码的标题
    4. 按照以下JSON格式返回:
    {result_schema}
    注意:只需返回合法JSON数组,不是字典,不要解释,注意level和pno是int类型,注意只需要输出当前目录页的目录信息，不要前面的参考信息"""
    #print(prompt)
    try:
        completion = client.chat.completions.create(
            model=model_exinfo,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": f"data:image/png;base64,{img_base64}",

                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        print(completion)
        raw_response = completion.choices[0].message.content
        #print(raw_response)
        cleaned_response = raw_response.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            import json5  # 需要安装json5库
            return json5.loads(cleaned_response)    
    except Exception as e:
        print(f"目录信息提取失败: {str(e)}")
        print(f"原始响应内容: {raw_response}")  # 添加错误日志
        return []  

def llm_text(toc) -> list:
    # 构建prompt
    result_schema = """{
        [{"level": int,"title": "str","pno": int}]
    }"""
    prompt = f"""请整理校对一下以上的目录信息，要求：
    1. 确保其中的目录层级最低是1
    2. 确保其中的目录层级与标题是合理一致的
    3. 提取每个条目标题和对应页码,如果有些标题没有页码,那么就跳过没有对应页码的标题
    4. 每个条目按照以下JSON格式返回:
    {result_schema}
    注意:只需返回合法JSON数组,不是字典,不要解释,注意level和pno是int类型"""
    #print(prompt)
    try:
        completion = client.chat.completions.create(
            model='model_text',
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": toc},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        #print(completion)
        raw_response = completion.choices[0].message.content
        #print(raw_response)
        cleaned_response = raw_response.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            import json5  # 需要安装json5库
            return json5.loads(cleaned_response)    
    except Exception as e:
        print(f"目录信息提取失败: {str(e)}")
        print(f"原始响应内容: {raw_response}")  # 添加错误日志
        return []  

def extract_image(doc, page_num: int = 1, max_size_mb: float = 9.0) -> Image.Image:
    """
    提取 PDF 的某一页并返回 PIL.Image 对象，确保图片大小不超过指定限制
    
    Args:
        page_num (int): 要提取的页码（从1开始）
        max_size_mb (float): 允许的最大图片大小（MB），默认为9MB
    
    Returns:
        PIL.Image.Image: 提取的页面图片
    
    Raises:
        ValueError: 如果页码无效
    """
    # 检查页码是否有效
    if page_num < 1 or page_num > doc.page_count:
        doc.close()
        raise ValueError(f"无效页码：{page_num}（文档共{doc.page_count}页）")
    
    # 加载指定页（PyMuPDF 页码从0开始）
    page = doc.load_page(page_num - 1)
    
    # 初始缩放因子
    zoom = 1
    max_bytes = max_size_mb * 1024 * 1024  # 转换为字节
    
    # 尝试获取合适大小的图片
    while zoom > 0.1:  # 设置最小缩放因子以避免无限循环
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # 检查图片大小
        img_bytes = pix.tobytes("png")
        if len(img_bytes) <= max_bytes:
            break
            
        # 如果太大，减小缩放因子
        zoom *= 0.8  # 每次减少10%
    else:
        # 如果缩放因子已经很小但图片仍然太大
        raise ValueError("无法在最小缩放因子下生成小于9MB的图片")
    
    # 将 pixmap 转换为 PIL.Image
    img = Image.open(io.BytesIO(img_bytes))
    
    return img

def add_toc(doc: fitz.Document, toc: list[dict], offset_page: int) -> None:
    """
    为PDF文档添加目录结构
    
    Args:
        doc: PyMuPDF文档对象
        toc: 目录结构列表，格式为[{"level": int, "title": str, "pno": int}]
        offset_page: 页码偏移量
    """
    try:
        # 修正页码偏移（根据检测到的漂移）
        # 设置目录（需包含完整的层级结构）
        toc_items = []
        for item in toc:
            if all(key in item for key in ["level", "title", "pno"]) and item["pno"] !=None:
                toc_items.append([
                    max(1,item["level"]), 
                    item["title"],
                    max(1, min(item["pno"] + offset_page, doc.page_count)),
                ])
            else:
                print(f"⚠️ 跳过不完整的目录项: {item}")
            
        # 平滑层级过渡（确保层级递增不超过1）
        for i in range(len(toc_items) - 1):
            curr_level = toc_items[i][0]
            next_level = toc_items[i + 1][0]    
            # 跳过有效过渡情况
            if next_level in (curr_level, curr_level + 1) or next_level < curr_level:
                continue             
            # 修正异常跳变
            toc_items[i + 1][0] = curr_level + 1
        doc.set_toc(toc_items)
    except Exception as e:
        print(f"添加目录失败: {str(e)}")
        raise

def download_pdf(doc):

    """
    将处理后的PDF文档保存到内存并返回字节流
    
    Args:
        doc: fitz.Document对象
        
    Returns:
        bytes: PDF文件的字节流
    """
    # 创建内存字节流
    pdf_bytes = io.BytesIO()
    
    # 将PDF保存到内存流
    doc.save(pdf_bytes, garbage=4, deflate=True)
    
    # 重置流位置到开头
    pdf_bytes.seek(0)
    
    return pdf_bytes.getvalue()

def process_pdf(upload):
    """
    处理 PDF 文件并返回处理后的图片

    Returns:
        PIL.Image.Image: 处理后的图片
    """
    try:
        start_time = time.time()
        progress_bar = st.sidebar.progress(0)
        status_text.text("Loading PDF...")
        progress_bar.progress(10)
        if isinstance(upload, str):
            # Default image path
            if not os.path.exists(upload):
                st.error(f"Default image not found at path: {upload}")
                return
            doc = fitz.open(upload)
        else:
            # Uploaded file
            image_bytes = upload.getvalue()
            doc = fitz.open("stream",image_bytes, "pdf")
        image = extract_image(doc, 1)
        pdf_name=llm_pdf_name(image)
        image_placeholder.image(image)
        pdf_text.write(f"正在处理的PDF:{pdf_name}")
        status_text.text("检测目录页...")
        progress_bar.progress(20)
        # 提取图片
        toc_pages = []
        consecutive_non_toc = 0
        MAX_CONSECUTIVE_NON_TOC = 10  # 允许最多2页非目录间隔
        for page_num in range(1, doc.page_count + 1):
            try:
                image = extract_image(doc, page_num)     
                test=llm_is_toc(image)     
                image_placeholder.write("正在检测的页面:")
                image_placeholder.image(image)
                result_placeholder.write(f"第 {page_num} 页是否是目录页: {test}")
                if test:
                    consecutive_non_toc = 0
                    if not toc_pages:  # 第一个目录页
                        print(f"🚩 开始检测到目录页：第 {page_num} 页")
                    toc_pages.append(page_num)
                else:
                    if toc_pages:
                        consecutive_non_toc += 1
                        if consecutive_non_toc > MAX_CONSECUTIVE_NON_TOC:
                            print(f"✅ 最终目录页范围：第 {min(toc_pages)}-{max(toc_pages)} 页")
                            break
            except Exception as e:
                print(f"处理第 {page_num} 页时出错: {str(e)}")
        status_text.text("处理目录页...")
        progress_bar.progress(30)
        toc=[]
        for page_num in toc_pages:
            print(f"正在处理第 {page_num} 页的目录信息...")
            image = extract_image(doc, page_num)
            #每个层级给一个示例
            seen_levels = set()  # 新增：用于跟踪已处理的层级
            toc_info=[]
            for item in toc:
                # 新增：如果层级已存在则跳过
                if item["level"] in seen_levels:
                    continue
                seen_levels.add(item["level"])
                toc_info.append(item)
            toc_temp=llm_extract_toc_info(image,toc_info)
            image_placeholder.write("正在处理的页面:")
            image_placeholder.image(image)
            result_placeholder.write(f"第 {page_num} 页的目录信息:")
            result_placeholder.write(toc_temp)
            for item in toc_temp:
                if all(key in item for key in ["level", "title", "pno"]) and item["pno"] !=None:
                    toc.extend([item])
                else:
                    print(f"⚠️ 跳过不完整的目录项: {item}")
        print(toc)
        if toc:
            status_text.text("使用LLM规范化TOC结构...")
            progress_bar.progress(55)
            try:
                toc_json_string = json.dumps(toc, ensure_ascii=False, indent=2)
                refined_toc = llm_toc_info(toc_json_string)
                if refined_toc and isinstance(refined_toc, list):
                    # Basic validation of refined_toc structure
                    is_valid_refined_toc = True
                    for item in refined_toc:
                        if not (isinstance(item, dict) and \
                                all(key in item for key in ["level", "title", "pno"]) and \
                                isinstance(item["level"], int) and \
                                isinstance(item["title"], str) and \
                                isinstance(item["pno"], int)):
                            is_valid_refined_toc = False
                            break
                    
                    if is_valid_refined_toc:
                        toc = refined_toc
                        print("LLM规范化后的TOC:")
                        print(toc)
                        result_placeholder.write("LLM规范化后的TOC:") # Show user the refined TOC
                        result_placeholder.json(toc) # Display as JSON for better readability
                    else:
                        print("⚠️ LLM规范化返回的TOC结构无效，将使用原始提取的TOC。")
                        result_placeholder.warning("LLM规范化返回的TOC结构无效，将使用原始提取的TOC。")
                else:
                    print("⚠️ LLM规范化未能返回有效的TOC，将使用原始提取的TOC。")
                    result_placeholder.warning("LLM规范化未能返回有效的TOC，将使用原始提取的TOC。")

            except Exception as e:
                print(f"LLM TOC规范化过程中发生错误: {str(e)}")
                result_placeholder.error(f"LLM TOC规范化过程中发生错误: {str(e)}")
        else:
            st.warning("TOC为空，跳过LLM规范化步骤。")

        status_text.text("检测目录漂移数...")
        progress=60
        progress_bar.progress(progress)
        offset_history = []
        max_page = min(toc_pages[-1] + 31, doc.page_count)  # 确保最多执行30次
        for page_num in range(toc_pages[-1]+1, max_page):
            try:
                print(f"第 {page_num} 页") 
                image = extract_image(doc, page_num)     
                image_placeholder.write("正在检测的页面:")
                image_placeholder.image(image)
                page=llm_drift(image) 
                for item in page:
                    if not all(key in item for key in ["title", "pno"]) or item["pno"]==None:
                        print(f"⚠️ 跳过不完整的目录项: {item}")
                        continue
                    title=item["title"]
                    pno=item["pno"]
                    for it in toc:
                        if title==it["title"] and item["pno"]==it["pno"]:
                            current_offset=page_num-pno
                            offset_history.append(current_offset)
                            progress+=2
                            progress_bar.progress(progress)
                            result_placeholder.write(f"第 {page_num} 页到：第 {pno} 页,漂移{current_offset}页")
                            print(f"🚩 检测{title}到：第 {page_num} 页,漂移{current_offset}页")
                if len(offset_history)>10 or page_num==max_page-1:
                    offset_page=mode(offset_history)
                    break
            except Exception as e:
                print(f"处理第 {page_num} 页时出错: {str(e)}")

        toc.insert(0, {"level": 1, "title": "目录", "pno": toc_pages[0]-offset_page})
        add_toc(doc,toc,offset_page)
        # Prepare download button
        st.sidebar.markdown("\n")
        st.sidebar.download_button(
            f"Download {pdf_name}.pdf", 
            download_pdf(doc), 
            "output.pdf", 
            "application/pdf",  # 修改为PDF的MIME类型,
            key=pdf_name
        )
        filename = os.path.basename(pdf_name)+".pdf"
        output_path = os.path.join("./output", filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        progress_bar.progress(100)
        processing_time = time.time() - start_time
        status_text.text(f"Completed in {processing_time:.2f} seconds")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.sidebar.error("Failed to process image")
        # Log the full error for debugging
        print(f"Error in fix_image: {traceback.format_exc()}")

def scan_and_process_pdfs():
    if not scan_lock.acquire(blocking=False):
        print("⚠️ 另一个任务正在运行，跳过本次扫描")
        return

    try:
        pdf_files = [
            os.path.join('./tmp', f) 
            for f in os.listdir('./tmp') 
            if f.lower().endswith('.pdf')
        ]
        for pdf_path in pdf_files:
            process_pdf(pdf_path)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    finally:
        scan_lock.release()
# UI Layout
col1, col2 = st.columns(2)
image_placeholder = col1.empty()
result_placeholder = col2.empty()
my_upload = st.sidebar.file_uploader("Upload PDF", type='pdf', accept_multiple_files=False)

# Information about limitations
with st.sidebar.expander("ℹ️Guidelines"):
    st.write("""
    - Supported formats: PDF
    - Must english filename
    """)

# Process the image
if my_upload is not None:
    process_pdf(upload=my_upload)
else:
    scan_and_process_pdfs()
    schedule.every(10).minutes.do(scan_and_process_pdfs)
    while True:
        schedule.run_pending()
        time.sleep(5)
    # Try default images in order of preference
