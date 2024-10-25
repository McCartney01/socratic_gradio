import gradio as gr
from openai import OpenAI
import os
import uuid
import json
import prompts

key = os.getenv('OPENAI_API_KEY') # api key here
max_try = 3
client = OpenAI(api_key=key, base_url='https://open.momodel.cn/v1')

def agent_calling(messages):
    count = 0
    while 1:
        count += 1
        try:
            completion = client.chat.completions.create(
                model='gpt-4o',
                messages=messages,
                stream=True
            )
            response = ""
            for chunk in completion:
                chunk_message = getattr(chunk.choices[0].delta, 'content', None)
                if chunk_message:
                    response += chunk_message
                yield response
            return
        except Exception as e:
            if count > max_try:
                raise Exception(f'调用AI代理时出错。错误：{e}')
            else:
                print('[警告] 调用AI代理时出错，正在重试...')

def load_steps():
    with open('temp/step.json', 'r', encoding='utf-8') as file:
        return json.load(file)

def get_file(chat_history):
    os.makedirs('history', exist_ok=True)
    filename = 'history/' + str(uuid.uuid4()) + '.json'
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(chat_history, file, ensure_ascii=False, indent=4)
    return filename

def chat_interface(message, current_step, messages, chat_history):
    global steps

    if not messages:
        # 开始新的步骤
        if current_step < len(steps):
            step = steps[current_step]
            gen = agent_calling([
                {'role': 'system', 'content': prompts.subtasks_start_system},
                {'role': 'user', 'content': prompts.subtasks_start + step}
            ])
            for response1 in gen:
                yield [response1], current_step, messages, chat_history
            chat_history.append(f"【老师】：{response1}")
            messages = [
                {'role': 'system', 'content': prompts.subtasks_system},
                {'role': 'user', 'content': prompts.subtasks + steps[current_step] + '\n#输出：'}
            ]
            gen = agent_calling(messages)
            for response2 in gen:
                yield [response1, response2], current_step, messages, chat_history
            messages.append({'role': 'assistant', 'content': response2})
            chat_history.append(f"【老师】：{response2}")
        
        # 全部步骤结束
        else:
            current_step = 0
            yield ["所有步骤已完成。是否要重新开始？"], current_step, messages, chat_history

        return
    
    else:
        messages.append({'role': 'user', 'content': message})
        chat_history.append(f"【学生】：{message}")
        gen = agent_calling(messages)
        flag = False
        for response in gen:
            if '【结束】' in response:
                flag = True
            else:
                yield [response], current_step, messages, chat_history
        messages.append({'role': 'assistant', 'content': response})
        chat_history.append(f"【老师】：{response}")
        if flag:
            response = response.replace('【结束】', '')
            yield [response], current_step, messages, chat_history
            current_step += 1
            messages = []
            gen = chat_interface("", current_step, messages, chat_history)
            for result in gen:
                n_response, current_step, messages, chat_history = result
                n_response.insert(0, response)
                yield n_response, current_step, messages, chat_history

def user(user_message, history):
    return "", history + [[user_message, None]]

def bot(history, current_step, messages, chat_history):
    user_message = history[-1][0]
    gen = chat_interface(user_message, current_step, messages, chat_history)
    for result in gen:
        bot_message, step, messages, chat_history = result
        if not history[-1][0] and step != current_step:
            history = history[:-(len(bot_message)-1)]
            current_step = step
        elif not history[-1][0]:
            history = history[:-len(bot_message)]
        for i in range(len(bot_message)):
            history.append([None, bot_message[i]])
        yield history, current_step, messages, chat_history

def reset():
    current_step = 0
    messages = []
    chat_history = []
    gen = chat_interface("", current_step, messages, chat_history)
    for result in gen:
        history = []
        bot_message, current_step, messages, chat_history = result
        for i in range(len(bot_message)):
            history.append([None, bot_message[i]])
        yield history, current_step, messages, chat_history

steps = load_steps()

# 创建Gradio界面
with gr.Blocks() as iface:
    
    # 初始化
    current_step = gr.State(value=0)
    messages = gr.State(value=[])
    chat_history = gr.State(value=[])

    chatbot = gr.Chatbot(label="对话历史", value=[])
    msg = gr.Textbox(label="输入")
    clear = gr.Button("开始对话 / 重新开始")
    download = gr.Button("下载记录")
    file_output = gr.File(label="Download", interactive=False)

    msg.submit(user, [msg, chatbot], [msg, chatbot]).then(bot, [chatbot, current_step, messages, chat_history], [chatbot, current_step, messages, chat_history])
    clear.click(reset, None, [chatbot, current_step, messages, chat_history])
    download.click(get_file, chat_history, file_output)

# 运行Gradio应用
if __name__ == "__main__":
    iface.queue(default_concurrency_limit=None)
    iface.launch(server_name="0.0.0.0")