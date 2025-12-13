### Command example for mutemusic (NACC)
```python3 main.py   --subject 00   --session 01   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```

### Test restarting from block

python main.py   --subject 03   --session 01 --blocks 1-10 --tasks mutemusic   --output output/AS_sub_02_ses_1   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri 

python soundtest.py