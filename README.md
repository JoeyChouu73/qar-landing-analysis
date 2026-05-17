# 绿色QAR着陆分析系统

这是一个基于 Streamlit 的网页应用。用户打开网页后，可以上传 CSV、XLSX 或 XLS 数据，并按 `tt.py` 中的固定绿色 QAR 规则进行评分、区间判定、飞行员分析、单航班分析和外部数据判定。

## 本机运行

```bash
pip install -r requirements.txt
streamlit run tt.py
```

启动后访问：

```text
http://localhost:8501
```

## 局域网共享

如果其他人和你在同一个局域网，可以这样启动：

```bash
streamlit run tt.py --server.address 0.0.0.0 --server.port 8501
```

然后让别人访问：

```text
http://你的电脑IP:8501
```

注意：你的电脑需要保持开机，防火墙需要允许 8501 端口访问。

## 部署到云服务器

在云服务器上安装 Python 后：

```bash
git clone 你的项目地址
cd 你的项目目录
pip install -r requirements.txt
streamlit run tt.py --server.address 0.0.0.0 --server.port 8501
```

服务器安全组或防火墙需要开放 8501 端口。生产环境建议再配置域名、HTTPS 和进程守护工具，例如 systemd、supervisor 或 Docker。

## 部署到 Streamlit Community Cloud

1. 把本目录上传到 GitHub 仓库。
2. 登录 Streamlit Community Cloud。
3. 选择该仓库。
4. Main file path 填写 `tt.py`。
5. 点击 Deploy。

部署完成后，所有人都可以通过生成的网址上传自己的数据文件并分析。上传的数据只保存在当前会话内，不会写入项目文件。

## 数据字段要求

完整分析建议数据文件包含原始 QAR 字段，例如：

```text
GLIDEANGLE, 平飘距离, 着陆垂直载荷, 入口高度, 入口空速, 入口下降率, 入口横向偏差,
拉开始高度, 20英尺下降率, 10英尺下降率, 收光油门杆高度, 接地横向偏差, 接地空速,
接地航迹交叉, 着陆滑跑方向不稳定, 最大姿态, 接地姿态, 最大坡度, 接地坡度,
收光油门杆下降率, 拉反推时机, 收反推空速, 收反推地速, 着陆操纵者, 所属大队, 技术等级
```

“外部数据判定”只要求文件中包含任意固定规则字段，系统会自动识别可判定列。

支持的文件格式：

```text
CSV, XLSX, XLS
```

CSV 建议使用 GBK 或 UTF-8 编码。
