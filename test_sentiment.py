from src.sentiment import analyze_journal
text = "我真的會被氣死！跟他說過一百次襪子不要亂丟，結果今天回家一看，客廳地上又是兩隻襪子屍體。跟他說這件事，他還一臉無辜問我『幹嘛那麼生氣』，他是不是聽不懂人話啊？"
result = analyze_journal(text)
print (result)
