# build_ffi.py
#
# Copyright (C) 2006-2022 wolfSSL Inc.
#
# This file is part of wolfSSL. (formerly known as CyaSSL)
#
# wolfSSL is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# wolfSSL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import sys
import re
from distutils.util import get_platform
from cffi import FFI
from wolfcrypt import __wolfssl_version__ as version
from wolfcrypt._build_wolfssl import wolfssl_inc_path, wolfssl_lib_path, ensure_wolfssl_src, make, make_flags, local_path

libwolfssl_path = ""

def get_libwolfssl():
    global libwolfssl_path
    if sys.platform == "win32":
        libwolfssl_path = os.path.join(wolfssl_lib_path(), "wolfssl.lib")
        if not os.path.exists(libwolfssl_path):
            return 0
        else:
            return 1
    else:
        libwolfssl_path = os.path.join(wolfssl_lib_path(), "libwolfssl.a")
        if not os.path.exists(libwolfssl_path):
            libwolfssl_path = os.path.join(wolfssl_lib_path(), "libwolfssl.so")
            if not os.path.exists(libwolfssl_path):
                return 0
            else:
                return 1
        else:
            return 1

def generate_libwolfssl():
    ensure_wolfssl_src(version)
    prefix = local_path("lib/wolfssl/{}/{}".format(
        get_platform(), version))
    make(make_flags(prefix))

if get_libwolfssl() == 0:
    generate_libwolfssl()
    get_libwolfssl()

# detect features if user has built against local wolfSSL library
# if they are not, we are controlling build options in _build_wolfssl.py
local_wolfssl = os.environ.get("USE_LOCAL_WOLFSSL")
if local_wolfssl is not None:
    # Try to do native wolfSSL/wolfCrypt feature detection.
    # Open <wolfssl/options.h> header to parse for #define's
    # This will throw a FileNotFoundError if not able to find options.h
    optionsHeaderPath = wolfssl_inc_path() + "/wolfssl/options.h"
    optionsHeader = open(optionsHeaderPath, 'r')
    optionsHeaderStr = optionsHeader.read()
    optionsHeader.close()
    featureDetection = 1
    sys.stderr.write("\nDEBUG: Found <wolfssl/options.h>, attempting native "
                     "feature detection\n")

else:
    optionsHeaderStr = ""
    featureDetection = 0
    sys.stderr.write("\nDEBUG: Skipping native feature detection, build not "
                     "using USE_LOCAL_WOLFSSL\n")

# default values
MPAPI_ENABLED = 1
SHA_ENABLED = 1
SHA256_ENABLED = 1
SHA384_ENABLED = 1
SHA512_ENABLED = 1
SHA3_ENABLED = 1
DES3_ENABLED = 1
AES_ENABLED = 1
HMAC_ENABLED = 1
RSA_ENABLED = 1
RSA_BLINDING_ENABLED = 1
ECC_TIMING_RESISTANCE_ENABLED = 1
ECC_ENABLED = 1
ED25519_ENABLED = 1
ED448_ENABLED = 1
KEYGEN_ENABLED = 1
CHACHA_ENABLED = 1
PWDBASED_ENABLED = 1
FIPS_ENABLED = 0
FIPS_VERSION = 0
ERROR_STRINGS_ENABLED = 1
ASN_ENABLED = 1
WC_RNG_SEED_CB_ENABLED = 0
AESGCM_STREAM = 1

# detect native features based on options.h defines
if featureDetection:
    MPAPI_ENABLED = 1 if '#define WOLFSSL_PUBLIC_MP' in optionsHeaderStr else 0
    SHA_ENABLED = 0 if '#define NO_SHA' in optionsHeaderStr else 1
    SHA256_ENABLED = 0 if '#define NO_SHA256' in optionsHeaderStr else 1
    SHA384_ENABLED = 1 if '#define WOLFSSL_SHA384' in optionsHeaderStr else 0
    SHA512_ENABLED = 1 if '#define WOLFSSL_SHA512' in optionsHeaderStr else 0
    SHA3_ENABLED = 1 if '#define WOLFSSL_SHA3' in optionsHeaderStr else 0
    DES3_ENABLED = 0 if '#define NO_DES3' in optionsHeaderStr else 1
    AES_ENABLED = 0 if '#define NO_AES' in optionsHeaderStr else 1
    CHACHA_ENABLED = 1 if '#define HAVE_CHACHA' in optionsHeaderStr else 0
    HMAC_ENABLED = 0 if '#define NO_HMAC' in optionsHeaderStr else 1
    RSA_ENABLED = 0 if '#define NO_RSA' in optionsHeaderStr else 1
    ECC_TIMING_RESISTANCE_ENABLED = 1 if '#define ECC_TIMING_RESISTANT' in optionsHeaderStr else 0
    RSA_BLINDING_ENABLED = 1 if '#define WC_RSA_BLINDING' in optionsHeaderStr else 0
    ECC_ENABLED = 1 if '#define HAVE_ECC' in optionsHeaderStr else 0
    ED25519_ENABLED = 1 if '#define HAVE_ED25519' in optionsHeaderStr else 0
    ED448_ENABLED = 1 if '#define HAVE_ED448' in optionsHeaderStr else 0
    KEYGEN_ENABLED = 1 if '#define WOLFSSL_KEY_GEN' in optionsHeaderStr else 0
    PWDBASED_ENABLED = 0 if '#define NO_PWDBASED' in optionsHeaderStr else 1
    ERROR_STRINGS_ENABLED = 0 if '#define NO_ERROR_STRINGS' in optionsHeaderStr else 1
    ASN_ENABLED = 0 if '#define NO_ASN' in optionsHeaderStr else 1
    WC_RNG_SEED_CB_ENABLED = 1 if '#define WC_RNG_SEED_CB' in optionsHeaderStr else 0
    AESGCM_STREAM = 1 if '#define WOLFSSL_AESGCM_STREAM' in optionsHeaderStr else 0

    if '#define HAVE_FIPS' in optionsHeaderStr:
        FIPS_ENABLED = 1
        version_match = re.search(r'#define HAVE_FIPS_VERSION\s+(\d+)', optionsHeaderStr)
        if version_match is not None:
            FIPS_VERSION = int(version_match.group(1))

if RSA_BLINDING_ENABLED and FIPS_ENABLED:
    # These settings can't coexist. See settings.h.
    RSA_BLINDING_ENABLED = 0


# build cffi module, wrapping native wolfSSL
ffibuilder = FFI()

cffi_libraries = ["wolfssl"]

# Needed for WIN32 functions in random.c
if sys.platform == "win32":
    cffi_libraries.append("Advapi32")

ffibuilder.set_source(
    "wolfcrypt._ffi",
    """
#ifdef __cplusplus
extern "C" {
#endif
    #include <wolfssl/options.h>
    #include <wolfssl/wolfcrypt/settings.h>

    #include <wolfssl/wolfcrypt/sha.h>
    #include <wolfssl/wolfcrypt/sha256.h>
    #include <wolfssl/wolfcrypt/sha512.h>
    #include <wolfssl/wolfcrypt/sha3.h>

    #include <wolfssl/wolfcrypt/hmac.h>

    #include <wolfssl/wolfcrypt/aes.h>
    #include <wolfssl/wolfcrypt/chacha.h>
    #include <wolfssl/wolfcrypt/des3.h>
    #include <wolfssl/wolfcrypt/asn.h>
    #include <wolfssl/wolfcrypt/pwdbased.h>

    #include <wolfssl/wolfcrypt/random.h>

    #include <wolfssl/wolfcrypt/rsa.h>
    #include <wolfssl/wolfcrypt/ecc.h>
    #include <wolfssl/wolfcrypt/ed25519.h>
    #include <wolfssl/wolfcrypt/ed448.h>
    #include <wolfssl/wolfcrypt/curve25519.h>
#ifdef __cplusplus
}
#endif

    int MPAPI_ENABLED = """ + str(MPAPI_ENABLED) + """;
    int SHA_ENABLED = """ + str(SHA_ENABLED) + """;
    int SHA256_ENABLED = """ + str(SHA256_ENABLED) + """;
    int SHA384_ENABLED = """ + str(SHA384_ENABLED) + """;
    int SHA512_ENABLED = """ + str(SHA512_ENABLED) + """;
    int SHA3_ENABLED = """ + str(SHA3_ENABLED) + """;
    int DES3_ENABLED = """ + str(DES3_ENABLED) + """;
    int AES_ENABLED = """ + str(AES_ENABLED) + """;
    int CHACHA_ENABLED = """ + str(CHACHA_ENABLED) + """;
    int HMAC_ENABLED = """ + str(HMAC_ENABLED) + """;
    int RSA_ENABLED = """ + str(RSA_ENABLED) + """;
    int RSA_BLINDING_ENABLED = """ + str(RSA_BLINDING_ENABLED) + """;
    int ECC_TIMING_RESISTANCE_ENABLED = """ + str(ECC_TIMING_RESISTANCE_ENABLED) + """;
    int ECC_ENABLED = """ + str(ECC_ENABLED) + """;
    int ED25519_ENABLED = """ + str(ED25519_ENABLED) + """;
    int ED448_ENABLED = """ + str(ED448_ENABLED) + """;
    int KEYGEN_ENABLED = """ + str(KEYGEN_ENABLED) + """;
    int PWDBASED_ENABLED = """ + str(PWDBASED_ENABLED) + """;
    int FIPS_ENABLED = """ + str(FIPS_ENABLED) + """;
    int FIPS_VERSION = """ + str(FIPS_VERSION) + """;
    int ASN_ENABLED = """ + str(ASN_ENABLED) + """;
    int WC_RNG_SEED_CB_ENABLED = """ + str(WC_RNG_SEED_CB_ENABLED) + """;
    int AESGCM_STREAM = """ + str(AESGCM_STREAM) + """;
    """,
    include_dirs=[wolfssl_inc_path()],
    library_dirs=[wolfssl_lib_path()],
    libraries=cffi_libraries,
)

_cdef = """
    extern int MPAPI_ENABLED;
    extern int SHA_ENABLED;
    extern int SHA256_ENABLED;
    extern int SHA384_ENABLED;
    extern int SHA512_ENABLED;
    extern int SHA3_ENABLED;
    extern int DES3_ENABLED;
    extern int AES_ENABLED;
    extern int CHACHA_ENABLED;
    extern int HMAC_ENABLED;
    extern int RSA_ENABLED;
    extern int RSA_BLINDING_ENABLED;
    extern int ECC_TIMING_RESISTANCE_ENABLED;
    extern int ECC_ENABLED;
    extern int ED25519_ENABLED;
    extern int ED448_ENABLED;
    extern int KEYGEN_ENABLED;
    extern int PWDBASED_ENABLED;
    extern int FIPS_ENABLED;
    extern int FIPS_VERSION;
    extern int ASN_ENABLED;
    extern int WC_RNG_SEED_CB_ENABLED;
    extern int AESGCM_STREAM;

    typedef unsigned char byte;
    typedef unsigned int word32;

    typedef struct { ...; } WC_RNG;
    typedef struct { ...; } OS_Seed;

    int wc_InitRng(WC_RNG*);
    int wc_RNG_GenerateBlock(WC_RNG*, byte*, word32);
    int wc_RNG_GenerateByte(WC_RNG*, byte*);
    int wc_FreeRng(WC_RNG*);
    int wc_GenerateSeed(OS_Seed* os, byte* seed, word32 sz);

    int wc_GetPkcs8TraditionalOffset(byte* input, word32* inOutIdx, word32 sz);
"""

if MPAPI_ENABLED:
    _cdef += """
    typedef struct { ...; } mp_int;

    int mp_init (mp_int * a);
    int mp_to_unsigned_bin (mp_int * a, unsigned char *b);
    int mp_read_unsigned_bin (mp_int * a, const unsigned char *b, int c);
    """

if SHA_ENABLED:
    _cdef += """
    typedef struct { ...; } wc_Sha;
    int wc_InitSha(wc_Sha*);
    int wc_ShaUpdate(wc_Sha*, const byte*, word32);
    int wc_ShaFinal(wc_Sha*, byte*);
    """

if SHA256_ENABLED:
    _cdef += """
    typedef struct { ...; } wc_Sha256;
    int wc_InitSha256(wc_Sha256*);
    int wc_Sha256Update(wc_Sha256*, const byte*, word32);
    int wc_Sha256Final(wc_Sha256*, byte*);
    """

if SHA384_ENABLED:
    _cdef += """
    typedef struct { ...; } wc_Sha384;
    int wc_InitSha384(wc_Sha384*);
    int wc_Sha384Update(wc_Sha384*, const byte*, word32);
    int wc_Sha384Final(wc_Sha384*, byte*);
    """

if SHA512_ENABLED:
    _cdef += """
    typedef struct { ...; } wc_Sha512;

    int wc_InitSha512(wc_Sha512*);
    int wc_Sha512Update(wc_Sha512*, const byte*, word32);
    int wc_Sha512Final(wc_Sha512*, byte*);
    """
if SHA3_ENABLED:
    _cdef += """
    typedef struct { ...; } wc_Sha3;
    int wc_InitSha3_224(wc_Sha3*, void *, int);
    int wc_InitSha3_256(wc_Sha3*, void *, int);
    int wc_InitSha3_384(wc_Sha3*, void *, int);
    int wc_InitSha3_512(wc_Sha3*, void *, int);
    int wc_Sha3_224_Update(wc_Sha3*, const byte*, word32);
    int wc_Sha3_256_Update(wc_Sha3*, const byte*, word32);
    int wc_Sha3_384_Update(wc_Sha3*, const byte*, word32);
    int wc_Sha3_512_Update(wc_Sha3*, const byte*, word32);
    int wc_Sha3_224_Final(wc_Sha3*, byte*);
    int wc_Sha3_256_Final(wc_Sha3*, byte*);
    int wc_Sha3_384_Final(wc_Sha3*, byte*);
    int wc_Sha3_512_Final(wc_Sha3*, byte*);
    """

if DES3_ENABLED:
    _cdef += """
        typedef struct { ...; } Des3;
        int wc_Des3_SetKey(Des3*, const byte*, const byte*, int);
        int wc_Des3_CbcEncrypt(Des3*, byte*, const byte*, word32);
        int wc_Des3_CbcDecrypt(Des3*, byte*, const byte*, word32);
    """

if AES_ENABLED:
    _cdef += """
    typedef struct { ...; } Aes;

    int wc_AesSetKey(Aes*, const byte*, word32, const byte*, int);
    int wc_AesCbcEncrypt(Aes*, byte*, const byte*, word32);
    int wc_AesCbcDecrypt(Aes*, byte*, const byte*, word32);
    int wc_AesCtrEncrypt(Aes*, byte*, const byte*, word32);
    """

if AES_ENABLED and AESGCM_STREAM:
    _cdef += """
    int  wc_AesInit(Aes* aes, void* heap, int devId);
    int wc_AesGcmInit(Aes* aes, const byte* key, word32 len,
        const byte* iv, word32 ivSz);
    int wc_AesGcmEncryptInit(Aes* aes, const byte* key, word32 len,
        const byte* iv, word32 ivSz);
    int wc_AesGcmEncryptInit_ex(Aes* aes, const byte* key, word32 len,
        byte* ivOut, word32 ivOutSz);
    int wc_AesGcmEncryptUpdate(Aes* aes, byte* out, const byte* in,
        word32 sz, const byte* authIn, word32 authInSz);
    int wc_AesGcmEncryptFinal(Aes* aes, byte* authTag,
        word32 authTagSz);
    int wc_AesGcmDecryptInit(Aes* aes, const byte* key, word32 len,
        const byte* iv, word32 ivSz);
    int wc_AesGcmDecryptUpdate(Aes* aes, byte* out, const byte* in,
        word32 sz, const byte* authIn, word32 authInSz);
    int wc_AesGcmDecryptFinal(Aes* aes, const byte* authTag,
        word32 authTagSz);
    """

if CHACHA_ENABLED:
    _cdef += """
    typedef struct { ...; } ChaCha;

    int wc_Chacha_SetKey(ChaCha*, const byte*, word32);
    int wc_Chacha_SetIV(ChaCha*, const byte*, word32);
    int wc_Chacha_Process(ChaCha*, byte*, const byte*,word32);
    """

if HMAC_ENABLED:
    _cdef += """
    typedef struct { ...; } Hmac;
    int wc_HmacInit(Hmac* hmac, void* heap, int devId);
    int wc_HmacSetKey(Hmac*, int, const byte*, word32);
    int wc_HmacUpdate(Hmac*, const byte*, word32);
    int wc_HmacFinal(Hmac*, byte*);
    """

if RSA_ENABLED:
    _cdef += """
    typedef struct {...; } RsaKey;

    int wc_InitRsaKey(RsaKey* key, void*);
    int wc_FreeRsaKey(RsaKey* key);

    int wc_RsaPrivateKeyDecode(const byte*, word32*, RsaKey*, word32);
    int wc_RsaPublicKeyDecode(const byte*, word32*, RsaKey*, word32);
    int wc_RsaEncryptSize(RsaKey*);

    int wc_RsaPrivateDecrypt(const byte*, word32, byte*, word32,
                            RsaKey* key);
    int wc_RsaPublicEncrypt(const byte*, word32, byte*, word32,
                            RsaKey*, WC_RNG*);

    int wc_RsaSSL_Sign(const byte*, word32, byte*, word32, RsaKey*, WC_RNG*);
    int wc_RsaSSL_Verify(const byte*, word32, byte*, word32, RsaKey*);
    """


    if RSA_BLINDING_ENABLED:
        _cdef += """
        int wc_RsaSetRNG(RsaKey* key, WC_RNG* rng);
        """

    if KEYGEN_ENABLED:
        _cdef += """
        int wc_MakeRsaKey(RsaKey* key, int size, long e, WC_RNG* rng);
        int wc_RsaKeyToDer(RsaKey* key, byte* output, word32 inLen);
        int wc_RsaKeyToPublicDer(RsaKey* key, byte* output, word32 inLen);

        """

if ECC_ENABLED:
    _cdef += """
    typedef struct {...; } ecc_key;

    int wc_ecc_init(ecc_key* ecc);
    void wc_ecc_free(ecc_key* ecc);

    int wc_ecc_make_key(WC_RNG* rng, int keysize, ecc_key* key);
    int wc_ecc_size(ecc_key* key);
    int wc_ecc_sig_size(ecc_key* key);

    int wc_EccPrivateKeyDecode(const byte*, word32*, ecc_key*, word32);
    int wc_EccKeyToDer(ecc_key*, byte* output, word32 inLen);

    int wc_EccPublicKeyDecode(const byte*, word32*, ecc_key*, word32);
    int wc_EccPublicKeyToDer(ecc_key*, byte* output,
                             word32 inLen, int with_AlgCurve);

    int wc_ecc_export_x963(ecc_key*, byte* out, word32* outLen);
    int wc_ecc_import_x963(const byte* in, word32 inLen, ecc_key* key);
    int wc_ecc_export_private_raw(ecc_key* key, byte* qx, word32* qxLen,
                              byte* qy, word32* qyLen, byte* d, word32* dLen);
    int wc_ecc_import_unsigned(ecc_key* key, byte* qx, byte* qy,
                   byte* d, int curve_id);
    int wc_ecc_export_public_raw(ecc_key* key, byte* qx, word32* qxLen,
                             byte* qy, word32* qyLen);


    int wc_ecc_shared_secret(ecc_key* private_key, ecc_key* public_key,
                             byte* out, word32* outlen);

    int wc_ecc_sign_hash(const byte* in, word32 inlen,
                         byte* out, word32 *outlen,
                         WC_RNG* rng, ecc_key* key);
    int wc_ecc_verify_hash(const byte* sig, word32 siglen,
                           const byte* hash, word32 hashlen,
                           int* stat, ecc_key* key);
    """

    if MPAPI_ENABLED:
        _cdef += """
        int wc_ecc_sign_hash_ex(const byte* in, word32 inlen, WC_RNG* rng,
                             ecc_key* key, mp_int *r, mp_int *s);
        int wc_ecc_verify_hash_ex(mp_int *r, mp_int *s, const byte* hash,
                        word32 hashlen, int* res, ecc_key* key);
        """

    if ECC_TIMING_RESISTANCE_ENABLED:
        _cdef += """
        int wc_ecc_set_rng(ecc_key* key, WC_RNG* rng);
        """


if ED25519_ENABLED:
    _cdef += """
    typedef struct {...; } ed25519_key;

    int wc_ed25519_init(ed25519_key* ed25519);
    void wc_ed25519_free(ed25519_key* ed25519);

    int wc_ed25519_make_key(WC_RNG* rng, int keysize, ed25519_key* key);
    int wc_ed25519_make_public(ed25519_key* key, unsigned char* pubKey,
                           word32 pubKeySz);
    int wc_ed25519_size(ed25519_key* key);
    int wc_ed25519_sig_size(ed25519_key* key);
    int wc_ed25519_sign_msg(const byte* in, word32 inlen, byte* out,
                        word32 *outlen, ed25519_key* key);
    int wc_ed25519_verify_msg(const byte* sig, word32 siglen, const byte* msg,
                          word32 msglen, int* stat, ed25519_key* key);
    int wc_Ed25519PrivateKeyDecode(const byte*, word32*, ed25519_key*, word32);
    int wc_Ed25519KeyToDer(ed25519_key*, byte* output, word32 inLen);

    int wc_Ed25519PublicKeyDecode(const byte*, word32*, ed25519_key*, word32);
    int wc_Ed25519PublicKeyToDer(ed25519_key*, byte* output,
                             word32 inLen, int with_AlgCurve);

    int wc_ed25519_import_public(const byte* in, word32 inLen, ed25519_key* key);
    int wc_ed25519_import_private_only(const byte* priv, word32 privSz, ed25519_key* key);
    int wc_ed25519_import_private_key(const byte* priv, word32 privSz, const byte* pub, word32 pubSz, ed25519_key* key);
    int wc_ed25519_export_public(ed25519_key*, byte* out, word32* outLen);
    int wc_ed25519_export_private_only(ed25519_key* key, byte* out, word32* outLen);
    int wc_ed25519_export_private(ed25519_key* key, byte* out, word32* outLen);
    int wc_ed25519_export_key(ed25519_key* key, byte* priv, word32 *privSz, byte* pub, word32 *pubSz);
    int wc_ed25519_check_key(ed25519_key* key);
    int wc_ed25519_pub_size(ed25519_key* key);
    int wc_ed25519_priv_size(ed25519_key* key);
    """

if ED448_ENABLED:
    _cdef += """
    typedef struct {...; } ed448_key;

    int wc_ed448_init(ed448_key* ed448);
    void wc_ed448_free(ed448_key* ed448);

    int wc_ed448_make_key(WC_RNG* rng, int keysize, ed448_key* key);
    int wc_ed448_make_public(ed448_key* key, unsigned char* pubKey,
                           word32 pubKeySz);
    int wc_ed448_size(ed448_key* key);
    int wc_ed448_sig_size(ed448_key* key);
    int wc_ed448_sign_msg(const byte* in, word32 inlen, byte* out,
                        word32 *outlen, ed448_key* key, byte* ctx,
                        word32 ctx_len);
    int wc_ed448_verify_msg(const byte* sig, word32 siglen, const byte* msg,
                          word32 msglen, int* stat, ed448_key* key, byte *ctx,
                          word32 ctx_len);
    int wc_Ed448PrivateKeyDecode(const byte*, word32*, ed448_key*, word32);
    int wc_Ed448KeyToDer(ed448_key*, byte* output, word32 inLen);

    int wc_Ed448PublicKeyDecode(const byte*, word32*, ed448_key*, word32);
    int wc_Ed448PublicKeyToDer(ed448_key*, byte* output,
                             word32 inLen, int with_AlgCurve);

    int wc_ed448_import_public(const byte* in, word32 inLen, ed448_key* key);
    int wc_ed448_import_private_only(const byte* priv, word32 privSz, ed448_key* key);
    int wc_ed448_import_private_key(const byte* priv, word32 privSz, const byte* pub, word32 pubSz, ed448_key* key);
    int wc_ed448_export_public(ed448_key*, byte* out, word32* outLen);
    int wc_ed448_export_private_only(ed448_key* key, byte* out, word32* outLen);
    int wc_ed448_export_private(ed448_key* key, byte* out, word32* outLen);
    int wc_ed448_export_key(ed448_key* key, byte* priv, word32 *privSz, byte* pub, word32 *pubSz);
    int wc_ed448_check_key(ed448_key* key);
    int wc_ed448_pub_size(ed448_key* key);
    int wc_ed448_priv_size(ed448_key* key);
    """

if PWDBASED_ENABLED:
    _cdef += """
    int wc_PBKDF2(byte* output, const byte* passwd, int pLen,
                  const byte* salt, int sLen, int iterations, int kLen,
                  int typeH);
    """

if ASN_ENABLED:
    _cdef += """
    static const long PRIVATEKEY_TYPE;
    static const long PUBLICKEY_TYPE;
    static const long CERT_TYPE;
    static const long MAX_DER_DIGEST_SZ;
    static const long SHAh;
    static const long SHA256h;
    static const long SHA384h;
    static const long SHA512h;

    typedef struct DerBuffer {
        byte*  buffer;
        void*  heap;
        word32 length;
        int    type;
        int    dynType;
    } DerBuffer;
    typedef struct { ...; } EncryptedInfo;

    int wc_PemToDer(const unsigned char* buff, long longSz, int type,
                    DerBuffer** pDer, void* heap, EncryptedInfo* info,
                    int* keyFormat);
    int wc_DerToPemEx(const byte* der, word32 derSz, byte* output, word32 outSz,
                      byte *cipher_info, int type);
    word32 wc_EncodeSignature(byte* out, const byte* digest, word32 digSz,
                              int hashOID);
    """

if WC_RNG_SEED_CB_ENABLED:
    _cdef += """
    typedef int (*wc_RngSeed_Cb)(OS_Seed* os, byte* seed, word32 sz);

    int wc_SetSeed_Cb(wc_RngSeed_Cb cb);
    """

if FIPS_ENABLED and (FIPS_VERSION > 5 or (FIPS_VERSION == 5 and FIPS_VERSION >= 1)):
    _cdef += """
    enum wc_KeyType {
        WC_KEYTYPE_ALL = 0
    };

    int wolfCrypt_SetPrivateKeyReadEnable_fips(int, enum wc_KeyType);
    int wolfCrypt_GetPrivateKeyReadEnable_fips(enum wc_KeyType);
    """

ffibuilder.cdef(_cdef)

ffibuilder.compile(verbose=True)