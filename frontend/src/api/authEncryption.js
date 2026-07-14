import request from './request'

const encoder = new TextEncoder()

export async function postEncryptedAuth(url, payload) {
  const keyInfo = await fetchEncryptionKey()
  const encryptedRequest = await encryptPayload(payload, keyInfo)
  return request.post(url, encryptedRequest)
}

async function fetchEncryptionKey() {
  const response = await request.get('/auth/encryption-key', {
    headers: { 'Cache-Control': 'no-cache' },
    silent: true
  })
  const keyInfo = response.data || response
  if (!keyInfo?.keyId || !keyInfo?.publicKey
    || keyInfo.keyAlgorithm !== 'RSA-OAEP-256'
    || keyInfo.contentAlgorithm !== 'AES-256-GCM') {
    throw new Error('服务器认证加密配置无效')
  }
  return keyInfo
}

async function encryptPayload(payload, keyInfo) {
  if (globalThis.crypto?.subtle) {
    try {
      return await encryptWithWebCrypto(payload, keyInfo)
    } catch {
      // 普通 HTTP 或旧浏览器的 Web Crypto 能力可能不完整，使用纯 JS 实现保持协议一致。
    }
  }
  return encryptWithForge(payload, keyInfo)
}

async function encryptWithWebCrypto(payload, keyInfo) {
  const publicKey = await crypto.subtle.importKey(
    'spki',
    pemToArrayBuffer(keyInfo.publicKey),
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    false,
    ['encrypt']
  )
  const aesKey = await crypto.subtle.generateKey(
    { name: 'AES-GCM', length: 256 },
    true,
    ['encrypt']
  )
  const rawAesKey = await crypto.subtle.exportKey('raw', aesKey)
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const additionalData = encoder.encode(keyInfo.keyId)
  const plaintext = encoder.encode(JSON.stringify(payload))

  const [encryptedKey, ciphertext] = await Promise.all([
    crypto.subtle.encrypt({ name: 'RSA-OAEP' }, publicKey, rawAesKey),
    crypto.subtle.encrypt(
      { name: 'AES-GCM', iv, additionalData, tagLength: 128 },
      aesKey,
      plaintext
    )
  ])

  return {
    keyId: keyInfo.keyId,
    encryptedKey: arrayBufferToBase64(encryptedKey),
    iv: arrayBufferToBase64(iv),
    ciphertext: arrayBufferToBase64(ciphertext)
  }
}

async function encryptWithForge(payload, keyInfo) {
  const { default: forge } = await import('node-forge')
  const publicKey = forge.pki.publicKeyFromPem(keyInfo.publicKey)
  const aesKey = forge.random.getBytesSync(32)
  const iv = forge.random.getBytesSync(12)
  const cipher = forge.cipher.createCipher('AES-GCM', aesKey)
  cipher.start({
    iv,
    additionalData: keyInfo.keyId,
    tagLength: 128
  })
  cipher.update(forge.util.createBuffer(JSON.stringify(payload), 'utf8'))
  if (!cipher.finish()) {
    throw new Error('认证请求加密失败')
  }

  const encryptedKey = publicKey.encrypt(aesKey, 'RSA-OAEP', {
    md: forge.md.sha256.create(),
    mgf1: { md: forge.md.sha256.create() }
  })
  const ciphertext = cipher.output.getBytes() + cipher.mode.tag.getBytes()
  return {
    keyId: keyInfo.keyId,
    encryptedKey: forge.util.encode64(encryptedKey),
    iv: forge.util.encode64(iv),
    ciphertext: forge.util.encode64(ciphertext)
  }
}

function pemToArrayBuffer(pem) {
  const base64 = pem
    .replace('-----BEGIN PUBLIC KEY-----', '')
    .replace('-----END PUBLIC KEY-----', '')
    .replace(/\s/g, '')
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes.buffer
}

function arrayBufferToBase64(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value)
  let binary = ''
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000))
  }
  return btoa(binary)
}
