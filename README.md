Если при создании токена Gigchat выдает ошибку:
```commandline
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain
```
Значит надо установить сертификаты Минцифры
```commandline
curl -k "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt" -w "\n" >> $(python -m certifi)
```