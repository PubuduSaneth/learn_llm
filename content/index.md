# Building Blocks of GPT-2 LLM

## Introduction

This lesson is designed to

- Explore the architecture of LLMs with a special focus on GPT-2 model
- Introduce fundamental components of LLM (i.e., building blocks of LLM architecture)
- Provide understanding of basic LLM architecture

## Objective

- Identify key components (building blocks) of LLM (Decoder-only LLMs)
- Understand
  - why each building block of a LLM important ?
  - how these building blocks work ?
- Understand the dataflow and data parallelization of LLMs

At the end of the lesson, learners will gain knowledge to interpret the processes that enable LLMs to predict the next word from a sequence of input words

:::{prereq}
Prerequisites

- Basic understanding of Deep learning concepts and methods
- Python programming
- Basic understanding of PyTorch implementation
:::


```{toctree}
:caption: The lesson
:maxdepth: 1

01.LLM_intro.md
02.GPT_intro.md
03.tokenizer.md
04.Embeddings.md
05.Transformer_block.md
06.Attention_mechanism.md
07.masked_attention.md
08.Multihead-attention.md
09.FNN.md
10.LM_head.md
10_1.LLM-end-t0-end.ipynb
11.LLM_dataflow.md
```

```{toctree}
:caption: Reference
:maxdepth: 1

quick-reference
```

(learner-personas)=

## Who is the tutorial for?

This lesson is for individuals with deep learning knowledge and want to have a basic overview of the architecture of LLMs. The lesson is designed not to dive deep into each component but to interpret the underline processes of LLM's key components.

## Credits
