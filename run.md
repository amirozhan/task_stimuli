### Command example for mutemusic (NACC)
```python3 main.py   --subject 00   --session 01   --tasks mutemusic   --output output/test_mgh_music   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri```

### Test restarting from block

 

python soundtest.py

python main.py   --subject 01   --session 03 --blocks 11-20 --tasks mutemusic   --output output/SH_sub_01_ses_03   --no-force-resolution   --run_on_battery   --skip-soundcheck --fmri