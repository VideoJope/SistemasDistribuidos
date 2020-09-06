import socket

HOST = ''   #interface padrao de comunicacao da maquina
PORT = 5000 #identifica o port do processo na maquina

#Cria o descritor de socket:
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP

#Vincula o endereco e porta:
sock.bind((HOST, PORT))

#Se posiciona em modo de espera:
sock.listen(1) #argumento indica quantidade de conexoes pendentes permitidas

print("Aguardando conexao...")

#Aceita conexao, bloqueia se nao houver pedidos de conexao:
newSock, address = sock.accept() #funcao retorna um novo socket -> tupla (socket, (ip, porta do socket))
print("Conectado com: " + str(address))

while True:
    #Espera por mensagem do lado ativo:
    msg = newSock.recv(1024) #bloqueia enquanto nao receber mensagem, argumento indica quantidade maxima de bytes
    if not msg: break #sai do loop se a mensagem nao for valida
    newSock.send(msg) #echo!
    print("Messagem recebida e reenviada: " + str(msg, encoding='utf-8'))

#Fecha o descritor de socket da conexao:
print("Conexao terminada!")
newSock.close()

#Fecha o descritor de socket principal da aplicacao passiva:
sock.close()