' Yuridik klinika boti - FONDA (oynasiz) ishga tushirish.
' Ikki marta bosing: bot ko'rinmas holda ishlaydi, oyna ochilmaydi.
' To'xtatish uchun: stop.bat
' Avval kamida bir marta start.bat ni ishga tushirgan bo'lishingiz kerak.

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = dir & "\.venv\Scripts\pythonw.exe"

If Not fso.FileExists(pyw) Or Not fso.FileExists(dir & "\.env") Then
    MsgBox "Avval start.bat ni bir marta ishga tushiring (token va ID kiritiladi," & vbCrLf & _
           "kutubxonalar o'rnatiladi). Keyin shu faylni qayta bosing.", 48, "Yuridik klinika boti"
    WScript.Quit 1
End If

sh.CurrentDirectory = dir
' 0 = oyna ko'rsatilmaydi, False = kutmasdan davom etadi
sh.Run """" & pyw & """ main.py", 0, False
