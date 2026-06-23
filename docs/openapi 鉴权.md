

## 对接文档（需要提供给调用方的内容）

### 1. 凭据（你分配给调用方）

| 凭据            | 用途                           | 示例值                                |
| ------------- | ---------------------------- | ---------------------------------- |
| **AppKey**    | 身份标识，每次请求在 Header 中携带        | `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6` |
| **AppSecret** | 签名密钥，**只在本地计算签名用，永远不出现在请求中** | `my-secret-xxxxx`                  |

### 2. 接口地址

| 方法  | 路径                                              | 说明         |
| --- | ----------------------------------------------- | ---------- |
| GET | `/ontology/api/open/domains`                    | 获取全部已发布域数据 |
| GET | `/ontology/api/open/domains/{domainId}`         | 获取指定域数据    |
| GET | `/ontology/api/open/datasources/{datasourceId}` | 获取数据源详情    |

### 3. 请求 Header（每次请求必带）

| Header        | 说明                          |
| ------------- | --------------------------- |
| `X-App-Key`   | 分配给您的 AppKey                |
| `X-Timestamp` | 当前 Unix 毫秒时间戳               |
| `X-Nonce`     | 任意唯一字符串（UUID、业务流水号等），每次请求不同 |
| `X-Signature` | 按下方算法计算的签名                  |

### 4. 签名算法

```
待签名字符串 = AppKey + 换行符(\n) + Timestamp + 换行符(\n) + Nonce
Signature = Base64(HMAC-SHA256(AppSecret, 待签名字符串))
```
