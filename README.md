要使用 `uv` 创建 Python 虚拟环境，可以按照以下步骤操作。`uv` 是由 Astral 开发的高效 Python 包管理工具，支持替代 `pip` 和 `virtualenv`，适合需要快速管理依赖的用户。

---

### **步骤 1：安装 `uv`**
通过 `pip` 安装
```bash
# 或使用 pip（全局安装）
pip install uv
```

---

### **步骤 2：创建虚拟环境**
使用 `uv venv` 命令创建虚拟环境：
```bash
uv venv myenv  # 创建名为 myenv 的虚拟环境
```
- **指定 Python 版本**：通过 `--python` 参数指定：
  ```bash
  uv venv --python 3.9 myenv  # 使用 Python 3.9
  ```

---

### **步骤 3：激活虚拟环境**
根据操作系统选择激活命令：
- **Linux/macOS**：
  ```bash
  source myenv/bin/activate
  ```
- **Windows**（PowerShell）：
  ```powershell
  .\myenv\Scripts\activate
  ```

---

### **步骤 4：使用 `uv` 管理依赖**
- **批量安装依赖**：  
  1. 将依赖写入 `requirements.txt`。  
  2. 运行以下命令安装所有依赖：
     ```bash
     uv pip install -r requirements.txt
     ```

- **运行**：  
  1. 将依赖写入 `requirements.txt`。  
  2. 运行以下命令安装所有依赖：
     ```bash
     streamlit run pdf.py
     ```
- **docker**：
     ```bash
    docker run -p 8501:8501 -v $(pwd)/tmp:/app/tmp -v $(pwd)/output:/app/output pdf-toc-generator
     ```  
