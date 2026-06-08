# 电脑维修风险告知确认程序（Streamlit 云端版）

这是用于 Streamlit Cloud/云端部署的版本。与原始版本不同，本版本不会把客户信息或生成的 PDF 写入云端文件系统。

## 隐私处理

- PDF 只在当前 Streamlit 会话内存中生成。
- 页面只提供 `下载 PDF` 按钮，由浏览器下载到使用者本地。
- 不创建 `outputs` 目录，不调用文件写入保存客户 PDF。
- 使用完成后可点击侧边栏 `重新开始` 清空当前页面状态。

## 本地运行

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 部署

1. 将本文件夹提交到 GitHub 仓库。
2. 在 Streamlit Cloud 新建应用时，主文件路径选择：

```text
streamlit_cloud_app/app.py
```

3. 依赖文件使用本目录下的 `requirements.txt`。

## 文件结构

- `app.py`：云端版 Streamlit 页面、逐项确认、签名、内存 PDF 和下载流程。
- `notice_content.py`：风险告知内容、确认声明和接机状态字段。
- `pdf_exporter.py`：仅返回 PDF bytes，不写入服务器文件。
- `requirements.txt`：部署依赖。
