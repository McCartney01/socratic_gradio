FROM python:3.9-slim

# 使用清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装所需的库
RUN pip install openai gradio

# 创建工作目录
WORKDIR /app

# 复制所有应用程序文件
COPY . .

# 设置环境变量，禁用Python输出缓冲
ENV PYTHONUNBUFFERED=1

# 暴露7860端口
EXPOSE 7860

# 设置运行命令
CMD ["python", "test_gradio.py"]
