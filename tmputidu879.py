

    
global z


if x > 10:
    if x > 20:
        if x > 30:
            if x > 40:
                print("Nested conditions!")
                
                
B108: Probable insecure usage of temp file/directory
temp = tempfile.mktemp()
with open(temp, 'w') as f:
    f.write(user_input)

B105: Hardcoded password string
db_password = "super_secret_password123"

B601: Possible shell injection via Paramiko
os.system(f"cat {filename}")

