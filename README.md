<img align="left" src="https://raw.githubusercontent.com/kovadarra/pupquiz/master/pupquiz/resources/icon.ico?raw=true">

# Pup Quiz

<br>

```
pip install pupquiz && py -m pupquiz
```

**Pup Quiz** facilitates vocabulary acquisition by employing [spaced repetition](https://en.wikipedia.org/wiki/Spaced_repetition) principles, quizzing words in a systematic order where words in a critical state are quizzed the most often, followed by a bucket of new words and then buckets of words of descending criticality. See [demo video](https://youtu.be/l-omUDVW778).

At the moment this tool is meant to be used together with [Boost Note](https://boostnote.io/). Present your word-definition list in a note followingly.
```
word 1
~ definition for word 1
word 2
~ definition for word 2
...
```
You can override this behavior in `%APPDATA%\pupquiz\config-user.json` (refer to `%APPDATA%\pupquiz\config-default.json`).
