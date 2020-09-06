import socket

HOST = 'localhost' #configuracao de ip da aplicacao passiva
PORT = 5000        #identifica o port do processo na maquina

#Cria descritor de socket
sock = socket.socket() #socket.AF_INET, socket.SOCK_STREAM sao passados como argumentos por default!

print('Tentando conectar...')
#Estabelece conexao:
sock.connect((HOST, PORT))
print('Conexao estabelecida! Envie \'exit\' como mensagem para encerrar conexao.')

while True:
    sendMessage = input('Mensagem a ser enviada: ')
    if sendMessage == 'exit': break
    #Envia mensagem:
    sock.send(str.encode(sendMessage))

    #Recebe mensagem do lado passivo:
    msg = sock.recv(1024)
    print(str(msg, encoding='utf-8'))

#Encerra a conexao:
print("Desconectando...")
sock.close()