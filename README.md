# finddd


# example

```python
import finddd

# get all dirs and files in current dir
files = finddd.find(r".", filetypes=[finddd.FT_DIRECTORY, finddd.FT_FILE],)
print(files)

```