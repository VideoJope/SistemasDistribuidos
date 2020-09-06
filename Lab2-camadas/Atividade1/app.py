from operator import itemgetter
from re import findall


#---CAMADA DE INTERFACE DE USUARIO---:
def userInterface():
    print("Aplicacao inicializada! Insira 'exit' como nome do arquivo para sair do programa.")
    while True:
        fileName = input("Nome do arquivo a ser lido: ")
        if (fileName == 'exit' or fileName == 'Exit'): #Sai do loop caso o usuario inserir 'exit'.
            break
        outData = processData(fileName) #Requere os dados já formatados do arquivo da Camada de Processamento de Dados.
        print(outData) #Imprime os dados.


#---CAMADA DE PROCESSAMENTO DE DADOS---:
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


#---CAMADA DE ACESSO A DADOS---:
def accessData(fileName):
    #Tenta abrir o arquivo desejado, retornando 'err' caso falhe, e retornando os dados em string contidos nele para a camada superior de processamento:
    try:
        fileObject = open(fileName, 'r')
        fileString = fileObject.read()
        fileObject.close()
    except:
        return 'err'
    return fileString


#---MAIN:---

#Chamada da Camada de Interface:
userInterface()