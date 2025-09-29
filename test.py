import monde
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify

for maxime in ['RUSSIE','URSS', 'CHINOIS', 'AMERICAIN']:
    print(f"Bonjour, {maxime} !")