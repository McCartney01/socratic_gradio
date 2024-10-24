import gradio as gr
from openai import OpenAI
import json
import prompts
import os
import uuid

key = os.getenv('OPENAI_API_KEY') # api key here
max_try = 3
client = OpenAI(api_key=key)

def agent_calling(messages):
    count = 0
    while 1:
        count += 1
        try:
            completion = client.chat.completions.create(
                model='gpt-4o',
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            if count > max_try:
                raise Exception(f'调用AI代理时出错。错误：{e}')
            else:
                print('[警告] 调用AI代理时出错，正在重试...')

def load_steps():
    with open('temp/step.json', 'r', encoding='utf-8') as file:
        return json.load(file)

def get_file(chat_history):
    filename = 'history/'+str(uuid.uuid4())+'.json'
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(chat_history, file, ensure_ascii=False, indent=4)
    return filename

def chat_interface(message, current_step, messages, chat_history):
    global steps

    if not messages:
        # 开始新的步骤
        if current_step < len(steps):
            step = steps[current_step]
            response1 = agent_calling([
                {'role': 'system', 'content': prompts.subtasks_start_system},
                {'role': 'user', 'content': prompts.subtasks_start + step}
            ])
            chat_history.append(f"【老师】：{response1}")
            messages = [
                {'role': 'system', 'content': prompts.subtasks_system},
                {'role': 'user', 'content': prompts.subtasks + steps[current_step] + '\n#输出：'}
            ]
            response2 = agent_calling(messages)
            messages.append({'role': 'assistant', 'content': response2})
            chat_history.append(f"【老师】：{response2}")
            # save_history(chat_history, filename)
            return [response1, response2], current_step, messages, chat_history
        
        # 全部步骤结束，程序自动保存
        else:
            current_step = 0
            # save_history(chat_history, filename)
            return ["所有步骤已完成。是否要重新开始？"], current_step, messages, chat_history
    
    # 跳过当前步骤
    if message.lower() == '\\skip':
        current_step += 1
        if current_step < len(steps): return ["好的，我们跳过这个步骤。"], current_step, messages, chat_history
        else:
            current_step = 0
            messages = []
            return ["好的，我们跳过这个步骤。", "所有步骤已完成。是否要重新开始？"], current_step, messages, chat_history
    
    else:
        messages.append({'role': 'user', 'content': message})
        chat_history.append(f"【学生】：{message}")
        response1 = agent_calling(messages)
        messages.append({'role': 'assistant', 'content': response1})
        chat_history.append(f"【老师】：{response1}")
        
        # 添加步骤结束后的完整代码检查
        if '【结束】' in response1:
            response1 = response1.replace('【结束】', '')
        #     messages = [
        #         {'role': 'system', 'content': prompts.subtasks_end_system},
        #         {'role': 'user', 'content': prompts.subtasks_end + steps[current_step]}
        #     ]
        #     response2 = agent_calling(messages)
        #     messages.append({'role': 'assistant', 'content': response2})
        #     chat_history.append(f"【老师】：{response2}")
        #     current_step += 1
        #     return [response1, response2]

        # # 当前步骤结束，进行下一步骤
        # elif '【正确】' in response1:
        #     response1 = response1.replace('【正确】', '')
            current_step += 1
            messages = []
            response, current_step, messages, chat_history = chat_interface("", current_step, messages, chat_history)
            response.insert(0, response1)
            return response, current_step, messages, chat_history

        return [response1], current_step, messages, chat_history

def user(user_message, history):
    return "", history + [[user_message, None]]

def bot(history, current_step, messages, chat_history):
    user_message = history[-1][0]
    bot_message, current_step, messages, chat_history = chat_interface(user_message, current_step, messages, chat_history)
    # save_history(chat_history, filename)
    for i in range(len(bot_message)):
        history.append([None, bot_message[i]])
    return history, current_step, messages, chat_history

def reset():
    current_step = 0
    messages = []
    chat_history = []
    bot_message, current_step, messages, chat_history = chat_interface("", current_step, messages, chat_history)
    history = [[None, bot_message[0]], [None, bot_message[1]]]
    # save_history(chat_history, filename)
    return history, current_step, messages, chat_history

steps = load_steps()

# 创建Gradio界面
with gr.Blocks() as iface:
    
    # 初始化
    current_step = gr.State(value=0)
    chat_history = gr.State(value=[])
    messages = gr.State(value=[])

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
    iface.queue()
    iface.launch(share=True)
