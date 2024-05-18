# install

```py
    # 'sub_commands': a list of commands this command might have to run to
    # get its work done.  See cmd.py for more info.
    sub_commands = [('install_lib',     has_lib),
                    ('install_headers', has_headers),
                    ('install_scripts', has_scripts),
                    ('install_data',    has_data),
                    ('install_egg_info', lambda self:True),
                   ]
```

## extend

* [setuptoolsを使ったインストール時に任意の処理を実行する](https://qiita.com/kokumura/items/c2f3670ee5baebdef86b)
