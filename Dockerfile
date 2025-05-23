# 使用官方 Python 运行时作为父镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.9-slim

# 安装 uv
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 复制依赖文件到工作目录
COPY requirements.txt .

# 使用 uv 安装项目依赖
RUN uv pip install --no-cache-dir -r requirements.txt --system

# 复制项目代码到工作目录
COPY pdf.py .
COPY config.json .

# 创建必要的目录 (如果你的应用会创建这些目录)
RUN mkdir -p /app/tmp
RUN mkdir -p /app/output

# 暴露 Streamlit 默认端口
EXPOSE 8501

# 运行 Streamlit 应用的命令
CMD ["streamlit", "run", "pdf.py", "--server.port=8501", "--server.address=0.0.0.0"]