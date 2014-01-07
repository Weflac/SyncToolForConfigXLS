#-*- coding: utf-8 -*-
#
import os
import sys
import syncTools
import codecs
from syncTools import ToolException
import chardet
import shutil

reload(sys)
sys.setdefaultencoding('utf-8')

def getpath():
    # path = './cmp'
    path = raw_input(u"   对比路径:".encode("gbk"))
    if os.path.exists('report.html'):
        os.remove('report.html')
    if os.path.exists('tempReport.txt'):
        os.remove('tempReport.txt')
    if os.path.exists(path):
        if os.path.isdir(path):
            for fileName in os.listdir(path):
                compare(os.path.join(path,fileName))
        else:
            compare(path)
    else:
        raise ToolException("对比路径不存在")
    os.system("report.html")

def compare(fileLeft):
    try:
        syncTools.loadConfig()
        syncTools.login(syncTools.host,syncTools.username,syncTools.password)
        tableName = syncTools.getTableName(fileLeft)
        if not os.path.exists("temp"):
            os.mkdir("temp")

        fileRight = os.path.join(".","temp","sever_"+os.path.basename(fileLeft))
        print "fileRight",fileRight
        syncTools.downloadTable(syncTools.host,tableName,fileRight)
        commandStr = "\"%s\" /silent @script.txt %s %s tempReport.txt" % (syncTools.bcomparePath, fileLeft,fileRight)
        # commandStr = "\"%s\" /silent @\"script.txt\" \"%s\" \"%s\" \"tempReport.txt\" " % (syncTools.bcomparePath, fileLeft,fileRight)
        print commandStr
        os.system(commandStr)
        appendReport()
        pass
    except Exception, e:
        print e.message
    pass
def appendReport():
    tempreport = open('tempReport.txt','rb')
    tempcontent = tempreport.read()
    report = open("report.html",'ab')
    report.write(tempcontent)
    tempreport.close()
    report.close()

getpath()
# syncTools.loadConfig()
# syncTools.login(syncTools.host,syncTools.username,syncTools.password)
# tableName = syncTools.getTableName("商城表(info_shop).xls")
# syncTools.downloadTable(syncTools.host,info_shop,tableName)
os.system("pause")