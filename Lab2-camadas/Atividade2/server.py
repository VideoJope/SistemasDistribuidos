import socket
from operator import itemgetter
from re import findall

HOST = ''   #interface padrao de comunicacao da maquina
PORT = 5000 #identifica o port do processo na maquina

#CAMADA DE PROCESSAMENTO DE DADOS:
def processData(fileName):
    fileString = accessData(fileName) #Requere os dados em formato de string da Camada de Acesso a Dados.
    if(fileString == 'err'): return "Erro! Arquivo invalido." #Retorna uma mensagem de erro caso nao tenha sido possivel ler o arquivo. 
    
    N = 10      #numero de palavras a ranquear
    words = {}  #dict de palavras

    words_list = findall(r'\w+', fileString.lower()) #lista de palavras (convertidas antes para letra minuscula) do arquivo texto

    #Armazena no dicionario as palavras e seu numero de ocorrencias:
    for word in words_list: 
        words[word] = words.get(word, 0) + 1

    #Realiza o sort e armazena o resultado na lista 'top_words':
    top_words = sorted(words.items(), key=itemgetter(1), reverse=True)[:N]

    #Armazena na string 'processedData' os dados ja processados e formatados para retornar a camada superior de interface para impressao:
    processedData = "Ranking de Ocorrencia de Palavras:\n"
    rank = 1
    for word, frequency in top_words:
        processedData = processedData + ("Rank %d: %s\t (%dx)\n" % (rank, word, frequency))
        rank += 1
    return processedData


#CAMADA DE ACESSO A DADOS:
def accessData(fileName):
    #Tenta abrir o arquivo desejado, retornando 'err' caso falhe, e retornando os dados em string contidos nele para a camada superior de processamento:
    try:
        fileObject = open(fileName, 'r')
        fileString = fileObject.read()
        fileObject.close()
    except:
        return 'err'
    return fileString


#MAIN:

#Cria o descritor de socket:
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #argumento indica comunicacao via internet e TCP

#Vincula o endereco e porta:
sock.bind((HOST, PORT))

#Se posiciona em modo de espera:
sock.listen(1) #argumento indica quantidade de conexoes pendentes permitidas

print('Aguardando conexao...')

#Aceita conexao, bloqueia se nao houver pedidos de conexao:
newSock, address = sock.accept() #funcao retorna um novo socket -> tupla (socket, (ip, porta do socket))
print('Conectado com: ' + str(address))

while True:
    #Espera por mensagem do lado ativo:
    fileNameBytes = newSock.recv(2048) #bloqueia enquanto nao receber mensagem, argumento indica quantidade maxima de bytes
    if not fileNameBytes: break #sai do loop se a mensagem recebida nao for valida
    #Converte a mensagem para string e realiza a chamada da Camada de Processamento:
    OutData = processData(str(fileNameBytes, encoding='utf-8'))
    #Converte o retorno da chamada da Camada de Processamento para bytes e envia esses dados de volta para o Cliente:
    newSock.send(str.encode(OutData))

#Fecha o descritor de socket da conexao:
print('Conexao terminada!')
newSock.close()
#Fecha o descritor de socket principal da aplicacao passiva:
sock.close()