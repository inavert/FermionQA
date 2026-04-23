# FermionQA
## 環境・リポジトリ構成
```
FermionQA
|
|- .github: GitHub CI/CDパイプラインの設定
|
|- fermionQAlib: Jupyter notebook用の関数・クラス
|
|- figure
|
|- results
|
|- Cappital_Review.ipynb: 物理モデルとアルゴリズムの考察
|
|- lowcapital_notebook.ipynb: ライブラリの練習
|
|- Requirements.txt
```

```bash zsh (ローカル Python 仮想環境下で作業)
git clone https://github.com/inavert/FermionQA.git
cd FermionQA
python -m venv .venv
source .venv/bin/activate
pip install -r Requirements.txt
```

{{- Cirq, OpenFermion が、 Numpy の最新より少し古い版に依存している場合がある。その時は pip や実行時にエラーに出てきた版で再度 Numpy を入れ直す。}}

## [VQE on Hubbard model](./Hubbard.ipynb)
### references
- [Observing ground-state properties of the Fermi-Hubbard model using a scalable algorithm on a quantum computer | Nature Communications](https://www.nature.com/articles/s41467-022-33335-4)


### VQE 
VQE（Variational Quantum Eigensolver）は、変分原理を利用してハミルトニアンの基底エネルギー（最小固有値）を近似的に求める手法です。

量子回路で表現できる試行状態（Ansatz）をパラメータ $\theta$ で定義し、
その状態に対するエネルギー期待値 $E(\theta)=\langle\psi(\theta)|H|\psi(\theta)\rangle$ を評価します。
変分原理により、任意の $\theta$ について $E(\theta)$ は真の基底エネルギー以上になるため、
この値が基底状態に最も近くなるようなパラメータを探索します。

基本的な操作は次のとおりです: 
1. 問題のハミルトニアンを定義し、Ansatz 回路（初期パラメータを含む）を設計
2. 現在のパラメータで量子状態 $|\psi(\theta)\rangle$ を準備
3. ハミルトニアンを測定可能な項に分解し、ショット測定からエネルギー期待値 (と勾配) を推定
4. 古典計算の最適化アルゴリズム（例: BayesMGD, SPSA 等）で次のパラメータを更新
5. 2〜4 を反復し、エネルギーが収束した時の最小期待値とパラメータを獲得

最終的に得られた最適パラメータを用いれば、基底状態近傍の量子状態を再準備して、
相関関数や占有数などの物理量評価、さらに時間発展シミュレーションへ拡張できます。








### Hubbard model


### review

