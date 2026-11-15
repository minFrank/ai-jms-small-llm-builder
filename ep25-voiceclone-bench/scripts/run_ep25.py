
# ep25 跑测框架脚本（纯 CPU、分段落盘）
# 执行方式：python run_ep25.py
import os, sys, time, json, hashlib, wave, subprocess, psutil
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['HF_HUB_DISABLE_XET'] = '1'
print("环境已设定：纯 CPU、XET 禁用、代理可配")
print("脚本已就绪，待启动 VoiceStudio 后执行实测")
print("脚本文件:", __file__)
