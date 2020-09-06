import socket

#---CAMADA DE INTERFACE DE USUARIO---:
def userInterface(sock):
    while True:
        fileName = input("Nome do arquivo a ser lido: ")
        if (fileName == 'exit' or fileName == 'Exit'): break #Sai do loop caso o usuario inserir 'exit'.
        sock.send(str.encode(fileName)) #Envia uma mensagem requerindo o arquivo de nome 'fileName'
        outData = sock.recv(2048) #Recebe os dados já formatados da Camada de Processamento de Dados contida no servidor.
        print(str(outData, encoding = 'utf-8')) #Imprime os dados.


#---MAIN---:

HOST = 'localhost' #configuracao de ip da aplicacao servidor
PORT = 5000        #identifica o port do processo na maquina

#Cria descritor de socket
sock = socket.socket() #socket.AF_INET, socket.SOCK_STREAM sao passados como argumentos por default!

print("Tentando conectar...")

#Estabelece conexao:
sock.connect((HOST, PORT))
print("Conexao estabelecida! Envie \'exit\' como mensagem para encerrar a conexao e fechar o programa.")

#Chamada da Camada de Interface de Usuário:
userInterface(sock)

#Encerra a conexao:
print('\nDesconectando...\n')
sock.close()