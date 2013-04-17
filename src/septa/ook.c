#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <glpk.h>

typedef struct { double rhs, pi; } v_data;
typedef struct { double low, cap, cost, x; } a_data;

#define node(v) ((v_data *)((v)->data))
#define arc(a) ((a_data *)((a)->data))

/*--------------------------------------------------*\
  This code taken from the GLPK manual found at
  http://www.cs.unb.ca/~bremner/docs/glpk/glpk.pdf
\*--------------------------------------------------*/

int main(int argc, char *argv[]){
  if(argc != 2){
    printf("usage: %s filename\n", argv[0]);
    return 1;
  }
  if(access(argv[0], R_OK) == -1) {
    printf("file %s is not readable!", argv[1]);
    return 1;
  }
  glp_graph *G;
  glp_vertex *v, *w;
  glp_arc *a;
  int i, ret;
  double sol;
  G = glp_create_graph(sizeof(v_data), sizeof(a_data));
  ret = glp_read_mincost(G,
			 offsetof(v_data, rhs),
			 offsetof(a_data, low),
			 offsetof(a_data, cap),
			 offsetof(a_data, cost),
			 argv[1]);
  if (ret) {
    return ret;
  }
  ret = glp_mincost_okalg(G,
			  offsetof(v_data, rhs),
			  offsetof(a_data, low),
			  offsetof(a_data, cap),
			  offsetof(a_data, cost),
			  &sol,
			  offsetof(a_data, x),
			  offsetof(v_data, pi));
  printf("ret = %d; sol = %5g\n", ret, sol);
  if (ret) {
    return ret;
  }
  for (i = 1; i <= G->nv; i++) {
    v = G->v[i];
    for (a = v->out; a != NULL; a = a->t_next) {
      w = a->head;
      printf("arc %d->%d: x = %5g; lambda = %5g\n",
	     v->i,
	     w->i,
	     arc(a)->x,
	     arc(a)->cost - (node(v)->pi - node(w)->pi));
    }
  }
  glp_delete_graph(G);
  return 0;
}
