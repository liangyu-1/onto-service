# vLLM 离线部署整理文档：Qwen3 Embedding / Reranker / bge-m3

## 一、当前背景与结论

本次目标是在内网 GPU 机器 `jmzmaster23129` 上，通过已有的 `vllm/vllm-openai:latest` 镜像，离线部署以下模型服务：

| 模型 | 类型 | Hugging Face 仓库 | 计划用途 |
|---|---|---|---|
| Qwen3-Embedding-4B | Embedding | Qwen/Qwen3-Embedding-4B | 文本向量化 |
| Qwen3-Embedding-8B | Embedding | Qwen/Qwen3-Embedding-8B | 文本向量化 |
| Qwen3-Reranker-4B | Reranker | Qwen/Qwen3-Reranker-4B | 检索结果重排序 |
| Qwen3-Reranker-8B | Reranker | Qwen/Qwen3-Reranker-8B | 检索结果重排序 |
| bge-m3 | Embedding | BAAI/bge-m3 | 多语言文本向量化 |

当前已经确认：

```text
vLLM 镜像：vllm/vllm-openai:latest
vLLM 版本：0.19.0
GPU 机器：jmzmaster23129
GPU 类型：NVIDIA A100 80GB PCIe，共 6 张
当前空闲 GPU：0、1、4、5
当前占用 GPU：2、3，被 gemma4 的 vLLM 服务占用
```

关键结论：

```text
vLLM 镜像里只有推理运行环境，不包含 Qwen3 和 bge-m3 模型权重。
内网 GPU 机器无法访问 huggingface.co，因此不能让 vLLM 在线自动拉模型。
需要先在本地 Windows 电脑下载完整模型目录，再传到内网 GPU 机器。
```

已经在本地 Windows 电脑下载好的模型目录为：

```text
E:\XM\models\bge-m3
E:\XM\models\Qwen3-Embedding-4B
E:\XM\models\Qwen3-Embedding-8B
E:\XM\models\Qwen3-Reranker-4B
E:\XM\models\Qwen3-Reranker-8B
```

在 Git Bash 中对应路径为：

```bash
/e/XM/models
```

本次更新后的推荐部署策略为：

```text
GPU 0：Qwen3-Embedding-4B + bge-m3
GPU 1：Qwen3-Reranker-4B
GPU 4：Qwen3-Embedding-8B
GPU 5：Qwen3-Reranker-8B
GPU 2、3：gemma4 继续占用，暂时不动
```

其中 `Qwen3-Embedding-4B` 和 `bge-m3` 可以放在同一张 A100 80GB 上，但两个容器不能都使用很高的 `--gpu-memory-utilization`。推荐先保守设置：

```text
Qwen3-Embedding-4B：--gpu-memory-utilization 0.45
bge-m3：--gpu-memory-utilization 0.25
```

---

## 二、本地 Windows 下载模型记录

由于本地电脑访问 Hugging Face 需要代理，打开 Git Bash 后先设置代理：

```bash
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897

curl -I https://huggingface.co
```

进入模型保存目录：

```bash
mkdir -p /e/XM/models
cd /e/XM/models
```

启用 Git LFS：

```bash
git lfs install
git lfs version
```

下载模型命令如下：

```bash
cd /e/XM/models

git clone https://huggingface.co/Qwen/Qwen3-Embedding-4B
git clone https://huggingface.co/Qwen/Qwen3-Embedding-8B
git clone https://huggingface.co/Qwen/Qwen3-Reranker-4B
git clone https://huggingface.co/Qwen/Qwen3-Reranker-8B
git clone https://huggingface.co/BAAI/bge-m3
```

下载完成后检查模型权重是否真的拉下来：

```bash
cd /e/XM/models/Qwen3-Embedding-4B
ls -lh
find . -maxdepth 1 -name "*.safetensors" -exec ls -lh {} \;
```

如果 `.safetensors` 文件只有几 KB，说明 Git LFS 没拉成功，需要重新执行：

```bash
cd /e/XM/models/Qwen3-Embedding-4B
git lfs pull
```

其他模型也可以按同样方式检查。

正常完整模型目录中一般应包含：

```text
config.json
tokenizer.json
tokenizer_config.json
special_tokens_map.json
model.safetensors.index.json
model-00001-of-xxxxx.safetensors
model-00002-of-xxxxx.safetensors
...
```

不要只传单个 `.safetensors` 文件，必须传整个模型目录。

---

## 三、传输模型到内网 GPU 机器

内网 GPU 机器上统一放到：

```text
/data/models/
```

最终目录结构建议为：

```text
/data/models/bge-m3
/data/models/Qwen3-Embedding-4B
/data/models/Qwen3-Embedding-8B
/data/models/Qwen3-Reranker-4B
/data/models/Qwen3-Reranker-8B
```

如果无法直接 `scp`，可以先打包，再通过跳板机、内网文件服务器或其他方式传输。

在 Git Bash 中打包示例：

```bash
cd /e/XM/models

tar -czvf Qwen3-Embedding-4B.tar.gz Qwen3-Embedding-4B
tar -czvf Qwen3-Embedding-8B.tar.gz Qwen3-Embedding-8B
tar -czvf Qwen3-Reranker-4B.tar.gz Qwen3-Reranker-4B
tar -czvf Qwen3-Reranker-8B.tar.gz Qwen3-Reranker-8B
tar -czvf bge-m3.tar.gz bge-m3
```

在跳板机hadoop000中执行：

```bash
cd /data

scp Qwen3-Embedding-4B.tar.gz ubd_jmz_deployer@10.191.23.129:/home/ubd_jmz_deployer
scp Qwen3-Embedding-8B.tar.gz ubd_jmz_deployer@10.191.23.129:/home/ubd_jmz_deployer
scp Qwen3-Reranker-4B.tar.gz ubd_jmz_deployer@10.191.23.129:/home/ubd_jmz_deployer
scp Qwen3-Reranker-8B.tar.gz ubd_jmz_deployer@10.191.23.129:/home/ubd_jmz_deployer
scp bge-m3.tar.gz ubd_jmz_deployer@10.191.23.129:/home/ubd_jmz_deployer
#自己再挨个mv到/data/models
```

传到 GPU 机器后解压：

```bash
cd /data/models

tar -xzvf Qwen3-Embedding-4B.tar.gz
tar -xzvf Qwen3-Embedding-8B.tar.gz
tar -xzvf Qwen3-Reranker-4B.tar.gz
tar -xzvf Qwen3-Reranker-8B.tar.gz
tar -xzvf bge-m3.tar.gz
```

传输完成后，在 GPU 机器上检查：

```bash
ls -lh /data/models

du -sh /data/models/Qwen3-Embedding-4B
du -sh /data/models/Qwen3-Embedding-8B
du -sh /data/models/Qwen3-Reranker-4B
du -sh /data/models/Qwen3-Reranker-8B
du -sh /data/models/bge-m3

find /data/models/Qwen3-Embedding-4B -maxdepth 1 -name "*.safetensors" -exec ls -lh {} \;
find /data/models/bge-m3 -maxdepth 1 -name "*.safetensors" -exec ls -lh {} \;
```

如果目录只有几 KB 或几 MB，基本就是模型权重没传完整，需要重新检查 Git LFS 下载结果。

---

## 四、内网 GPU 机器环境确认

在 `jmzmaster23129` 上已经确认 GPU 情况：

```bash
nvidia-smi
```

当前机器为 6 张 A100 80GB，其中 GPU 2、3 已经被 `gemma4` 占用：

```text
GPU 2 -> VLLM::Worker_TP0，约 75170MiB
GPU 3 -> VLLM::Worker_TP1，约 75170MiB
```

查看 Docker 镜像：

```bash
docker images | grep vllm
```

当前存在：

```text
vllm/vllm-openai   latest   22bea3378819   2 months ago   22.4GB
vllm/vllm-openai   gemma4   131dfe5904ca   8 weeks ago    22.5GB
```

查看 vLLM 版本时需要使用 `python3`，不是 `python`：

```bash
docker run --rm \
  --gpus '"device=0"' \
  --entrypoint bash \
  vllm/vllm-openai:latest \
  -lc "which python3 && python3 -c 'import vllm; print(vllm.__version__)'"
```

实际返回：

```text
/usr/bin/python3
0.19.0
```

之前启动失败的原因不是 GPU 问题，也不是 vLLM 镜像问题，而是内网机器无法解析 Hugging Face 域名：

```text
Failed to resolve 'huggingface.co'
Temporary failure in name resolution
```

因此后续启动模型时必须使用本地模型路径，例如：

```bash
--model /models/Qwen3-Embedding-4B
```

不要再使用 Hugging Face 仓库名，例如：

```bash
--model Qwen/Qwen3-Embedding-4B
```

否则 vLLM 会继续尝试联网下载模型。

---

## 五、vLLM 服务启动命令

本次推荐使用 4 张空闲 GPU 部署 5 个服务，其中 `Qwen3-Embedding-4B` 和 `bge-m3` 共同部署在 GPU 0 上。

最终推荐规划如下：

| GPU | 服务 | 宿主机端口 | 容器端口 | 说明 |
|---|---|---:|---:|---|
| GPU 0 | Qwen3-Embedding-4B | 8102 | 8000 | 与 bge-m3 共用 GPU 0 |
| GPU 0 | bge-m3 | 8105 | 8000 | 与 Qwen3-Embedding-4B 共用 GPU 0 |
| GPU 1 | Qwen3-Reranker-4B | 8104 | 8000 | 单独一张卡 |
| GPU 4 | Qwen3-Embedding-8B | 8101 | 8000 | 单独一张卡 |
| GPU 5 | Qwen3-Reranker-8B | 8103 | 8000 | 单独一张卡 |
| GPU 2、3 | gemma4 | 已占用 | 已占用 | 暂时不动 |

注意事项：

```text
两个容器可以使用同一张 GPU，只要都指定 --gpus '"device=0"' 即可。
两个服务的容器内部端口都可以是 8000，因为容器之间相互隔离。
宿主机端口必须不同，例如 8102:8000 和 8105:8000。
同一张卡上不要让两个服务都使用 --gpu-memory-utilization 0.85。
```

### 5.1 启动 Qwen3-Embedding-4B

使用 GPU 0，宿主机端口 `8102`：

```bash
docker rm -f qwen3-embedding-4b 2>/dev/null || true

docker run -d \
  --name qwen3-embedding-4b \
  --gpus '"device=0"' \
  --ipc=host \
  -p 8102:8000 \
  -v /data/models:/models \
  vllm/vllm-openai:latest \
  --model /models/Qwen3-Embedding-4B \
  --served-model-name Qwen3-Embedding-4B \
  --host 0.0.0.0 \
  --port 8000 \
  --runner pooling \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.45
```

查看日志：

```bash
docker logs -f qwen3-embedding-4b
```

测试接口：

```bash
curl http://127.0.0.1:8102/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3-Embedding-4B",
    "input": [
      "HDFS 是什么？",
      "HDFS 是 Hadoop 的分布式文件系统。"
    ],
    "encoding_format": "float"
  }'
```

返回中出现 `embedding` 数组即为成功。

### 5.2 启动 bge-m3

使用 GPU 0，宿主机端口 `8105`：

```bash
docker rm -f bge-m3 2>/dev/null || true

docker run -d \
  --name bge-m3 \
  --gpus '"device=0"' \
  --ipc=host \
  -p 8105:8000 \
  -v /data/models:/models \
  vllm/vllm-openai:latest \
  --model /models/bge-m3 \
  --served-model-name bge-m3 \
  --host 0.0.0.0 \
  --port 8000 \
  --runner pooling \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.25
```

查看日志：

```bash
docker logs -f bge-m3
```

测试接口：

```bash
curl http://127.0.0.1:8105/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bge-m3",
    "input": [
      "HDFS 是什么？",
      "HDFS 是 Hadoop 的分布式文件系统，用于存储大规模数据。"
    ],
    "encoding_format": "float"
  }'
```

返回中出现 `embedding` 数组即为成功。

### 5.3 启动 Qwen3-Reranker-4B

使用 GPU 1，宿主机端口 `8104`：

```bash
docker rm -f qwen3-reranker-4b 2>/dev/null || true

docker run -d \
  --name qwen3-reranker-4b \
  --gpus '"device=1"' \
  --ipc=host \
  -p 8104:8000 \
  -v /data/models:/models \
  vllm/vllm-openai:latest \
  --model /models/Qwen3-Reranker-4B \
  --served-model-name Qwen3-Reranker-4B \
  --host 0.0.0.0 \
  --port 8000 \
  --runner pooling \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85 \
  --hf-overrides '{"architectures":["Qwen3ForSequenceClassification"],"classifier_from_token":["no","yes"],"is_original_qwen3_reranker":true}'
```

查看日志：

```bash
docker logs -f qwen3-reranker-4b
```

测试 Reranker 接口：

```bash
cat > test_rerank_4b.json <<'JSON'
{
  "model": "Qwen3-Reranker-4B",
  "query": "HDFS 文件读取流程是什么？",
  "documents": [
    "HDFS 读取文件时，客户端会先向 NameNode 请求文件块位置，然后根据返回的 DataNode 地址读取数据块。",
    "今天中午食堂有红烧肉、米饭和青菜。"
  ],
  "top_n": 2
}
JSON

curl http://127.0.0.1:8104/v1/rerank \
  -H "Content-Type: application/json" \
  -d @test_rerank_4b.json
```

返回中出现 `relevance_score` 说明服务可用。

### 5.4 启动 Qwen3-Embedding-8B

使用 GPU 4，宿主机端口 `8101`：

```bash
docker rm -f qwen3-embedding-8b 2>/dev/null || true

docker run -d \
  --name qwen3-embedding-8b \
  --gpus '"device=4"' \
  --ipc=host \
  -p 8101:8000 \
  -v /data/models:/models \
  vllm/vllm-openai:latest \
  --model /models/Qwen3-Embedding-8B \
  --served-model-name Qwen3-Embedding-8B \
  --host 0.0.0.0 \
  --port 8000 \
  --runner pooling \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85
```

查看日志：

```bash
docker logs -f qwen3-embedding-8b
```

测试接口：

```bash
curl http://127.0.0.1:8101/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3-Embedding-8B",
    "input": [
      "HDFS 是什么？",
      "HDFS 是 Hadoop 的分布式文件系统。"
    ],
    "encoding_format": "float"
  }'
```

返回中出现 `embedding` 数组即为成功。

### 5.5 启动 Qwen3-Reranker-8B

使用 GPU 5，宿主机端口 `8103`：

```bash
docker rm -f qwen3-reranker-8b 2>/dev/null || true

docker run -d \
  --name qwen3-reranker-8b \
  --gpus '"device=5"' \
  --ipc=host \
  -p 8103:8000 \
  -v /data/models:/models \
  vllm/vllm-openai:latest \
  --model /models/Qwen3-Reranker-8B \
  --served-model-name Qwen3-Reranker-8B \
  --host 0.0.0.0 \
  --port 8000 \
  --runner pooling \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.85 \
  --hf-overrides '{"architectures":["Qwen3ForSequenceClassification"],"classifier_from_token":["no","yes"],"is_original_qwen3_reranker":true}'
```

查看日志：

```bash
docker logs -f qwen3-reranker-8b
```

测试接口：

```bash
cat > test_rerank_8b.json <<'JSON'
{
  "model": "Qwen3-Reranker-8B",
  "query": "HDFS 文件读取流程是什么？",
  "documents": [
    "HDFS 读取文件时，客户端会先向 NameNode 请求文件块位置，然后根据返回的 DataNode 地址读取数据块。",
    "今天中午食堂有红烧肉、米饭和青菜。"
  ],
  "top_n": 2
}
JSON

curl http://127.0.0.1:8103/v1/rerank \
  -H "Content-Type: application/json" \
  -d @test_rerank_8b.json
```

返回中出现 `relevance_score` 说明服务可用。

---

## 六、运维检查与排错记录

### 6.1 查看当前容器

```bash
docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

### 6.2 查看指定容器日志

```bash
docker logs -f qwen3-embedding-4b
docker logs -f bge-m3
docker logs -f qwen3-reranker-4b
docker logs -f qwen3-embedding-8b
docker logs -f qwen3-reranker-8b
```

### 6.3 查看 GPU 占用

```bash
nvidia-smi
```

或者持续刷新：

```bash
watch -n 1 nvidia-smi
```

如果同卡部署成功，GPU 0 上应能看到两个 vLLM 进程，分别对应 `Qwen3-Embedding-4B` 和 `bge-m3`。

### 6.4 停止并删除容器

```bash
docker rm -f qwen3-embedding-4b
docker rm -f bge-m3
docker rm -f qwen3-reranker-4b
docker rm -f qwen3-embedding-8b
docker rm -f qwen3-reranker-8b
```

### 6.5 常见问题

#### 问题 1：日志里出现 `Failed to resolve 'huggingface.co'`

原因：内网机器无法访问 Hugging Face。

解决方式：不要使用 `--model Qwen/Qwen3-Embedding-4B`，改成本地模型路径：

```bash
--model /models/Qwen3-Embedding-4B
```

并确保 Docker 挂载了模型目录：

```bash
-v /data/models:/models
```

#### 问题 2：`python: command not found`

原因：vLLM 镜像中命令是 `python3`，不是 `python`。

检查版本应使用：

```bash
python3 -c 'import vllm; print(vllm.__version__)'
```

#### 问题 3：模型目录传了，但 vLLM 仍然找不到模型

检查宿主机目录：

```bash
ls -lh /data/models/Qwen3-Embedding-4B
```

检查容器挂载路径：

```bash
docker run --rm \
  --entrypoint bash \
  -v /data/models:/models \
  vllm/vllm-openai:latest \
  -lc "ls -lh /models/Qwen3-Embedding-4B"
```

如果容器里看不到模型，说明 `-v /data/models:/models` 挂载不对。

#### 问题 4：`.safetensors` 文件很小

原因：Git LFS 没有真正拉取大文件。

在本地 Windows Git Bash 中重新执行：

```bash
cd /e/XM/models/Qwen3-Embedding-4B
git lfs pull
```

然后重新传输。

#### 问题 5：两个服务部署在同一张 GPU 后显存不足

原因：两个 vLLM 服务都预留了过高的显存，或者 `max-model-len` 过大导致 KV Cache 预留较多。

解决方式：先降低同卡服务的显存比例，例如：

```text
Qwen3-Embedding-4B：--gpu-memory-utilization 0.40
bge-m3：--gpu-memory-utilization 0.20
```

如果仍然不稳，就把 `bge-m3` 单独挪到 GPU 4 或 GPU 5，先保证服务跑通。

### 6.6 当前推荐执行顺序

最稳顺序如下：

```text
第一步：传 Qwen3-Embedding-4B 到 /data/models，启动 GPU 0 的 8102 服务
第二步：传 bge-m3 到 /data/models，继续部署在 GPU 0，启动 8105 服务
第三步：传 Qwen3-Reranker-4B，部署在 GPU 1，启动 8104 服务
第四步：传 Qwen3-Embedding-8B，部署在 GPU 4，启动 8101 服务
第五步：传 Qwen3-Reranker-8B，部署在 GPU 5，启动 8103 服务
```

推荐对外服务地址：

```text
Qwen3-Embedding-8B:   http://GPU机器IP:8101/v1/embeddings
Qwen3-Embedding-4B:   http://GPU机器IP:8102/v1/embeddings
Qwen3-Reranker-8B:    http://GPU机器IP:8103/v1/rerank
Qwen3-Reranker-4B:    http://GPU机器IP:8104/v1/rerank
bge-m3:               http://GPU机器IP:8105/v1/embeddings
```

当前阶段重点不是调性能，而是先完成离线模型传输和服务启动验证。等五个服务都能正常返回结果后，再考虑是否需要统一网关、Nginx 转发、服务自启动、systemd 管理或 Kubernetes 部署。
